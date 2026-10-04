"""Run the real Windows OpenCode CLI against a scripted loopback provider. No inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LAB = Path(__file__).resolve().parents[1]
PIN = '3104c1428ec91f809e5ab86631300de41eb6952e'
BINARY_SHA256 = 'c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea'
CASES = [('allow', 'allow', False), ('ask', 'ask', False),
         ('ask_auto', 'ask', True), ('deny_auto', 'deny', True)]
EDIT = {'filePath': 'slug.mjs', 'oldString': ".replaceAll(' ', '-')",
        'newString': r".replace(/\s+/g, '-')"}


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def execute(command, case, stem, cwd, env, timeout=180):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=timeout)
    (case / (stem + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
    (case / (stem + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
    write_json(case / (stem + '.process.json'), {'command': command, 'exit': result.returncode})
    return result


def snapshot(workspace, destination):
    destination.mkdir()
    manifest = {}
    for item in sorted(workspace.iterdir()):
        if item.is_file():
            data = item.read_bytes()
            (destination / item.name).write_bytes(data)
            manifest[item.name] = {'sha256': sha(data), 'bytes': len(data)}
    write_json(destination / 'manifest.json', manifest)


def run_case(root, cli, node, shell, name, action, auto):
    case = root / name
    workspace = case / 'workspace'
    workspace.mkdir(parents=True)
    for fixture in (LAB / 'fixtures').iterdir():
        # Normalize the fixture checkout's line endings so Git autocrlf does not
        # become an independent variable in the runtime comparison.
        (workspace / fixture.name).write_bytes(fixture.read_text(encoding='utf-8').encode())
    subprocess.run(['git', '-c', 'init.templateDir=', 'init', '--quiet', str(workspace)],
                   check=True, capture_output=True)
    for directory in ['home', 'config', 'data', 'cache', 'state', 'temp']:
        (case / directory).mkdir()
    lock = threading.Lock()
    request_count = 0

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            nonlocal request_count
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            with lock:
                request_count += 1
                index = request_count
            if index > 16 or self.path != '/v1/chat/completions':
                self.send_error(400, 'Unexpected provider request')
                return
            write_json(case / f'request-{index:02}.json', {'path': self.path, 'body': payload})
            advertised = [t.get('function', {}).get('name') for t in payload.get('tools', [])]
            replies = [m for m in payload.get('messages', []) if m.get('role') == 'tool']
            tool = None
            text = 'Controlled call sequence finished.' if advertised else 'Synthetic permission task'
            if advertised and not replies:
                tool = {'index': 0, 'id': 'lab_read', 'type': 'function',
                        'function': {'name': 'read', 'arguments': json.dumps({'filePath': 'slug.mjs'})}}
            elif advertised and len(replies) == 1:
                tool = {'index': 0, 'id': 'lab_edit', 'type': 'function',
                        'function': {'name': 'edit', 'arguments': json.dumps(EDIT)}}
            message = {'role': 'assistant', 'content': text}
            finish = 'stop'
            if tool:
                message = {'role': 'assistant', 'tool_calls': [tool]}
                finish = 'tool_calls'
            write_json(case / f'response-{index:02}.json', {'message': message, 'finish_reason': finish})
            usage = {'prompt_tokens': 10, 'completion_tokens': 1, 'total_tokens': 11}
            if not payload.get('stream'):
                body = json.dumps({'id': 'lab', 'object': 'chat.completion', 'model': 'scripted',
                                   'choices': [{'index': 0, 'message': message, 'finish_reason': finish}],
                                   'usage': usage}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
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

    server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    config = {
        'model': 'lab/scripted', 'small_model': 'lab/scripted', 'default_agent': 'build',
        'enabled_providers': ['lab'], 'share': 'disabled', 'autoupdate': False, 'username': 'lab',
        'snapshot': False, 'lsp': False, 'formatter': False, 'shell': str(shell),
        'permission': {'*': 'deny', 'read': {'*': 'deny', 'slug.mjs': 'allow'},
                       'edit': {'*': 'deny', 'slug.mjs': action}},
        'provider': {'lab': {'npm': '@ai-sdk/openai-compatible', 'name': 'Scripted fixture',
                            'options': {'baseURL': f'http://127.0.0.1:{server.server_port}/v1', 'apiKey': 'lab'},
                            'models': {'scripted': {'name': 'No inference',
                                                   'limit': {'context': 32768, 'output': 4096}}}}},
    }
    write_json(case / 'opencode.json', config)
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP',
        'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'LANG', 'LC_ALL'}}
    env.update({'OPENCODE_CONFIG': str(case / 'opencode.json'),
                'OPENCODE_CONFIG_DIR': str(case / 'config'),
                'OPENCODE_TEST_HOME': str(case / 'home'),
                'HOME': str(case / 'home'), 'USERPROFILE': str(case / 'home'),
                'TEMP': str(case / 'temp'), 'TMP': str(case / 'temp'),
                'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'OPENCODE_DISABLE_MODELS_FETCH': 'true',
                'OPENCODE_DISABLE_PROJECT_CONFIG': 'true', 'OPENCODE_PURE': 'true',
                'XDG_DATA_HOME': str(case / 'data'), 'XDG_CONFIG_HOME': str(case / 'config'),
                'XDG_CACHE_HOME': str(case / 'cache'), 'XDG_STATE_HOME': str(case / 'state'),
                'NO_COLOR': '1'})
    env['PATH'] = str(node.parent) + os.pathsep + env.get('PATH', '')
    write_json(case / 'environment-keys.json', sorted(env))
    write_json(case / 'case.json', {'name': name, 'action': action, 'auto': auto})
    try:
        for kind, extra in [('config', []), ('agent', ['build'])]:
            result = execute([str(cli), 'debug', kind, *extra, '--pure'], case,
                             'resolved-' + kind, workspace, env, timeout=60)
            if result.returncode:
                raise RuntimeError(f'{name}: could not inspect effective {kind}; see private logs')
        snapshot(workspace, case / 'before')
        execute([str(node), '--test', 'slug.test.mjs'], case, 'test-before', workspace, env, 30)
        command = [str(cli), '--print-logs', '--log-level', 'INFO', 'run', '--pure',
                   '--format', 'json', '--model', 'lab/scripted', '--agent', 'build',
                   '--title', 'Synthetic permission boundary']
        if auto:
            command.append('--auto')
        command += ['--', 'Inspect slug.mjs, then replace repeated whitespace with one separator.']
        result = execute(command, case, 'cli', workspace, env)
        snapshot(workspace, case / 'after')
        execute([str(node), '--test', 'slug.test.mjs'], case, 'test-after', workspace, env, 30)
        events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        sessions = {e['sessionID'] for e in events if 'sessionID' in e}
        if len(sessions) != 1:
            raise RuntimeError(f'{name}: expected one recorded session, got {len(sessions)}')
        exported = execute([str(cli), 'export', sessions.pop()], case, 'export', workspace, env, 60)
        if exported.returncode:
            raise RuntimeError(f'{name}: session export failed')
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    print(f'Captured {name}: {request_count} provider requests', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', required=True, type=Path)
    parser.add_argument('--node', type=Path, default=shutil.which('node'))
    parser.add_argument('--shell', type=Path, default=shutil.which('pwsh'))
    parser.add_argument('--output', required=True, type=Path, help='Private parent directory outside the checkout')
    args = parser.parse_args()
    if platform.system() != 'Windows':
        parser.error('Fresh runtime execution is documented for Windows; offline checks are portable.')
    if not all(p and Path(p).is_file() for p in [args.opencode, args.node, args.shell]):
        parser.error('Existing OpenCode, Node and PowerShell executables are required.')
    output = args.output.resolve()
    if output.is_relative_to(LAB.parents[4]):
        parser.error('Raw evidence must be outside the repository checkout.')
    cli, node, shell = [Path(p).resolve() for p in [args.opencode, args.node, args.shell]]
    if sha(cli.read_bytes()) != BINARY_SHA256:
        parser.error('Expected the official v1.18.30 Windows x64 release binary; SHA256 differs.')
    version = subprocess.run([str(cli), '--version'], capture_output=True, text=True, check=True, timeout=30).stdout.strip()
    if version != '1.18.30':
        parser.error(f'Expected OpenCode 1.18.30; found {version}')
    output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='permissions-', dir=output))
    write_json(root / 'run.json', {'release': version, 'commit': PIN, 'platform': platform.system(),
                                  'architecture': platform.machine(), 'binary_sha256': sha(cli.read_bytes()),
                                  'python': platform.python_version(),
                                  'node': subprocess.run([str(node), '--version'], capture_output=True, text=True,
                                                         check=True, timeout=30).stdout.strip()})
    print(root, flush=True)
    for name, action, auto in CASES:
        run_case(root, cli, node, shell, name, action, auto)
    print('Raw capture complete. Run verify_run.py against this private directory.', flush=True)


if __name__ == '__main__':
    main()
