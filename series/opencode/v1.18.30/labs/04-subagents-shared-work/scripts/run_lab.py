"""Real Windows OpenCode delegation with a scripted loopback provider. No model inference."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contract import BINARY_SHA256, CHECK, EDIT, FILES, LAB, PIN, PROMPT, SUMMARY, TASK, fixture, policy, sha

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def execute(command, root, stem, workspace, env, timeout=180):
    result = subprocess.run(command, cwd=workspace, env=env, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    (root / (stem + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
    (root / (stem + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
    write_json(root / (stem + '.process.json'), {'command': command, 'exit': result.returncode})
    return result

def snapshot(workspace, destination):
    destination.mkdir()
    manifest = {}
    for file in sorted(workspace.rglob('*')):
        relative = file.relative_to(workspace)
        if '.git' in relative.parts or not file.is_file():
            continue
        data = file.read_bytes()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest[relative.as_posix()] = {'sha256': sha(data), 'bytes': len(data)}
    write_json(destination / 'manifest.json', manifest)

def run(root, cli, node, shell):
    workspace = root / 'workspace'
    workspace.mkdir()
    for name in FILES:
        (workspace / name).write_bytes(fixture(name))
    subprocess.run(['git', '-c', 'init.templateDir=', 'init', '--quiet', str(workspace)],
                   check=True, capture_output=True)
    for name in ['home', 'config', 'data', 'cache', 'state', 'temp']:
        (root / name).mkdir()
    lock = threading.Lock()
    sequence = []
    identities = {}
    errors = []
    count = 0

    def event(kind, **details):
        # Requests can arrive concurrently. The barrier itself has a strict local order.
        with lock:
            sequence.append({'order': len(sequence) + 1, 'kind': kind, **details})
            write_json(root / 'sequence.json', sequence)

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            nonlocal count
            try:
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                with lock:
                    count += 1
                    index = count
                if index > 20 or self.path != '/v1/chat/completions':
                    raise ValueError('unexpected provider request path or count')
                # Do not retain authorization headers, even in the private capture.
                headers = {k.lower(): v for k, v in self.headers.items()
                           if k.lower() in ['x-session-affinity', 'x-session-id', 'x-parent-session-id']}
                write_json(root / f'request-{index:02}.json', {'path': self.path, 'headers': headers, 'body': body})
                event('request_received', request=index)
                tools = {t['function']['name'] for t in body.get('tools', [])}
                replies = [m for m in body.get('messages', []) if m.get('role') == 'tool']
                reply_ids = [m['tool_call_id'] for m in replies]
                call = None
                content = 'Synthetic label task'
                kind = 'auxiliary'
                if 'task' in tools:
                    kind = 'parent'
                    identities['parent'] = headers['x-session-id']
                    if not replies:
                        call = ('parent_task', 'task', TASK)
                    elif reply_ids == ['parent_task']:
                        call = ('parent_check', 'bash', CHECK)
                    elif reply_ids == ['parent_task', 'parent_check']:
                        content = 'Parent received the task report and fixed test output. External checks follow.'
                    else:
                        raise ValueError('unexpected parent tool history')
                elif {'read', 'edit'} <= tools:
                    kind = 'child'
                    identities['child'] = headers['x-session-id']
                    if not replies:
                        call = ('child_read_helper', 'read', {'filePath': 'labels.mjs'})
                    elif reply_ids == ['child_read_helper']:
                        call = ('child_read_tests', 'read', {'filePath': 'labels.test.mjs'})
                    elif reply_ids == ['child_read_helper', 'child_read_tests']:
                        call = ('child_edit', 'edit', EDIT)
                    elif reply_ids == ['child_read_helper', 'child_read_tests', 'child_edit']:
                        # The request already carries the edit result. Read shared bytes
                        # before emitting any part of the final child response.
                        event('child_edit_result_received', request=index)
                        snapshot(workspace, root / 'before-report')
                        event('independent_file_checkpoint', request=index)
                        content = SUMMARY
                    else:
                        raise ValueError('unexpected child tool history')
                message = {'role': 'assistant', 'content': content}
                finish = 'stop'
                if call:
                    call_id, name, arguments = call
                    if name not in tools:
                        raise ValueError('controlled tool is not advertised')
                    message = {'role': 'assistant', 'tool_calls': [{'index': 0, 'id': call_id, 'type': 'function',
                               'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
                    finish = 'tool_calls'
                write_json(root / f'response-{index:02}.json', {'kind': kind, 'message': message, 'finish_reason': finish})
                write_json(root / 'identities.json', identities)
                if content == SUMMARY and call is None:
                    event('child_report_release', request=index)
                usage = {'prompt_tokens': 20, 'completion_tokens': 2, 'total_tokens': 22}
                self.send_response(200)
                if not body.get('stream'):
                    payload = json.dumps({'id': 'lab', 'object': 'chat.completion', 'model': 'scripted',
                              'choices': [{'index': 0, 'message': message, 'finish_reason': finish}], 'usage': usage}).encode()
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Content-Length', str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Connection', 'close')
                self.end_headers()
                for delta, reason in [(message, None), ({}, finish)]:
                    chunk = {'id': 'lab', 'object': 'chat.completion.chunk', 'model': 'scripted',
                             'choices': [{'index': 0, 'delta': delta, 'finish_reason': reason}]}
                    if reason:
                        chunk['usage'] = usage
                    self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
                self.wfile.write(b'data: [DONE]\n\n')
                self.wfile.flush()
            except Exception as exc:
                errors.append(str(exc))
                write_json(root / 'provider-errors.json', errors)
                self.send_error(500, 'controlled provider failed; inspect private capture')

    server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    config = {'model': 'lab/scripted', 'small_model': 'lab/scripted', 'default_agent': 'build',
              'enabled_providers': ['lab'], 'share': 'disabled', 'autoupdate': False, 'username': 'lab',
              'snapshot': False, 'lsp': False, 'formatter': False, 'shell': str(shell),
              'subagent_depth': 1, 'permission': {'*': 'deny'}, 'agent': policy(),
              'provider': {'lab': {'npm': '@ai-sdk/openai-compatible', 'name': 'Scripted fixture',
                'options': {'baseURL': f'http://127.0.0.1:{server.server_port}/v1', 'apiKey': 'lab'},
                'models': {'scripted': {'name': 'No inference', 'limit': {'context': 32768, 'output': 4096}}}}}}
    write_json(root / 'opencode.json', config)
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'PROCESSOR_ARCHITECTURE',
        'NUMBER_OF_PROCESSORS', 'LANG', 'LC_ALL'}}
    env.update({'OPENCODE_CONFIG': str(root / 'opencode.json'), 'OPENCODE_CONFIG_DIR': str(root / 'config'),
                'OPENCODE_TEST_HOME': str(root / 'home'), 'HOME': str(root / 'home'), 'USERPROFILE': str(root / 'home'),
                'TEMP': str(root / 'temp'), 'TMP': str(root / 'temp'),
                'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'OPENCODE_DISABLE_MODELS_FETCH': 'true',
                'OPENCODE_DISABLE_PROJECT_CONFIG': 'true', 'OPENCODE_PURE': 'true',
                'XDG_DATA_HOME': str(root / 'data'), 'XDG_CONFIG_HOME': str(root / 'config'),
                'XDG_CACHE_HOME': str(root / 'cache'), 'XDG_STATE_HOME': str(root / 'state'), 'NO_COLOR': '1'})
    env['PATH'] = str(node.parent) + os.pathsep + env.get('PATH', '')
    write_json(root / 'environment-keys.json', sorted(env))
    try:
        for stem, args in [('config', ['config']), ('parent', ['agent', 'build']), ('child', ['agent', 'general'])]:
            result = execute([str(cli), 'debug', *args, '--pure'], root, 'resolved-' + stem, workspace, env, 60)
            if result.returncode:
                raise RuntimeError('effective configuration capture failed')
        execute(['git', 'rev-parse', '--show-toplevel'], root, 'worktree', workspace, env, 30)
        snapshot(workspace, root / 'before')
        execute([str(node), '--test', 'labels.test.mjs'], root, 'test-before', workspace, env, 30)
        result = execute([str(cli), '--print-logs', '--log-level', 'INFO', 'run', '--pure', '--format', 'json',
                          '--model', 'lab/scripted', '--agent', 'build', '--title', 'Synthetic shared work', '--', PROMPT],
                         root, 'cli', workspace, env)
        snapshot(workspace, root / 'after')
        execute([str(node), '--test', 'labels.test.mjs'], root, 'test-after', workspace, env, 30)
        if errors or set(identities) != {'parent', 'child'}:
            raise RuntimeError('provider or session identification failed; inspect private captures')
        for kind, session_id in identities.items():
            exported = execute([str(cli), 'export', session_id], root, 'export-' + kind, workspace, env, 60)
            if exported.returncode:
                raise RuntimeError(kind + ' session export failed')
        print(f'Captured {count} provider requests; CLI exit {result.returncode}. Verify the evidence separately.', flush=True)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', required=True, type=Path)
    parser.add_argument('--node', type=Path, default=shutil.which('node'))
    parser.add_argument('--shell', type=Path, default=shutil.which('pwsh'))
    parser.add_argument('--output', required=True, type=Path, help='Private output parent outside this checkout')
    args = parser.parse_args()
    if platform.system() != 'Windows':
        parser.error('Fresh runtime execution is documented for Windows. Offline checks are portable.')
    if not all(p and p.is_file() for p in [args.opencode, args.node, args.shell]):
        parser.error('Existing OpenCode, Node and PowerShell executables are required.')
    cli, node, shell = [p.resolve() for p in [args.opencode, args.node, args.shell]]
    if sha(cli.read_bytes()) != BINARY_SHA256:
        parser.error('Expected official OpenCode v1.18.30 Windows x64 binary digest.')
    version = subprocess.run([str(cli), '--version'], capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    if version != '1.18.30':
        parser.error('Expected OpenCode 1.18.30.')
    output = args.output.resolve()
    if output.is_relative_to(LAB.parents[4]):
        parser.error('Raw evidence must remain outside the repository checkout.')
    output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='subagents-', dir=output))
    checkout = LAB.parents[4]
    revision = subprocess.run(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    changes = subprocess.run(['git', '-C', str(checkout), 'status', '--porcelain', '--untracked-files=all', '--', str(LAB)],
                             capture_output=True, text=True, check=True).stdout
    write_json(root / 'run.json', {'release': version, 'commit': PIN, 'binary_sha256': BINARY_SHA256,
        'platform': platform.system(), 'architecture': platform.machine(), 'python': platform.python_version(),
        'lab_revision': revision, 'lab_dirty': bool(changes), 'runner_sha256': sha(Path(__file__).read_bytes()),
        'shell_version': subprocess.run([str(shell), '-NoProfile', '-Command', '$PSVersionTable.PSVersion.ToString()'],
                                       capture_output=True, text=True, check=True).stdout.strip(),
        'node': subprocess.run([str(node), '--version'], capture_output=True, text=True, check=True).stdout.strip()})
    print(root, flush=True)
    run(root, cli, node, shell)

if __name__ == '__main__':
    main()
