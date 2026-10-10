"""Run controlled permission-location comparisons through OpenCode serve + run --attach.

The loopback provider scripts proposals, never model decisions. Raw captures stay private.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from boundary_contract import (BINARY_SHA256, CASES, CHANGED, DENIED, DIRECT_PROMPT, FILES, LAB,
                               PARENT_FINAL, PIN, PROMPT, SUCCESS, TASK, calls, fixture, roles, session_rules, sha)
from run_lab import execute, snapshot, write_json

def run_case(root, case, cli, node):
    workspace = root / 'workspace'
    workspace.mkdir(parents=True)
    for name in FILES:
        (workspace / name).write_bytes(fixture(name))
    subprocess.run(['git', '-c', 'init.templateDir=', 'init', '--quiet', str(workspace)], check=True, capture_output=True)
    for name in ('home', 'config', 'data', 'cache', 'state', 'temp'):
        (root / name).mkdir()
    count, errors, identities = 0, [], {}
    lock = threading.Lock()
    sequence = []
    def event(kind, **kw):
        with lock:
            sequence.append({'order': len(sequence) + 1, 'kind': kind, **kw})
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
                if index > 16 or self.path != '/v1/chat/completions':
                    raise ValueError('unexpected request count or path')
                headers = {k.lower(): v for k, v in self.headers.items()
                           if k.lower() in ('x-session-affinity', 'x-session-id', 'x-parent-session-id')}
                write_json(root / f'request-{index:02}.json', {'path': self.path, 'headers': headers, 'body': body})
                available = {t['function']['name'] for t in body.get('tools', [])}
                kind = 'auxiliary'
                if available:
                    kind = 'parent' if headers.get('x-session-id') == identities['parent'] else 'child'
                    if kind == 'child':
                        if identities.get('child', headers['x-session-id']) != headers['x-session-id']:
                            raise ValueError('multiple child identities')
                        identities['child'] = headers['x-session-id']
                replies = [m for m in body.get('messages', []) if m['role'] == 'tool']
                steps = [c for c in calls(case) if c[0].startswith(kind + '_')]
                reply_ids = [m['tool_call_id'] for m in replies]
                if reply_ids != [c[0] for c in steps[:len(replies)]]:
                    raise ValueError('unexpected tool history')
                content = 'Synthetic delegation boundary'
                call = steps[len(replies)] if len(replies) < len(steps) else None
                if not call and kind == 'child':
                    # Observe actual bytes after edit feedback, before releasing final text.
                    snapshot(workspace, root / 'before-report')
                    event('file_checkpoint_before_report', request=index)
                    content = DENIED if 'permission' in replies[-1]['content'].lower() and 'deny' in replies[-1]['content'].lower() else SUCCESS
                elif not call and kind == 'parent':
                    content = PARENT_FINAL
                message = {'role': 'assistant', 'content': content}
                finish = 'stop'
                if call:
                    call_id, name, arguments = call
                    if name not in available:
                        raise ValueError('proposal tool was not advertised')
                    message = {'role': 'assistant', 'tool_calls': [{'index': 0, 'id': call_id, 'type': 'function',
                               'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
                    finish = 'tool_calls'
                write_json(root / f'response-{index:02}.json', {'kind': kind, 'message': message, 'finish_reason': finish})
                write_json(root / 'identities.json', identities)
                event('response_release', request=index, kind_owner=kind, finish=finish)
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
                for delta, reason in ((message, None), ({}, finish)):
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
                self.send_error(500, 'fixture provider failed')

    provider = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    provider.daemon_threads = True
    thread = threading.Thread(target=provider.serve_forever, daemon=True)
    thread.start()
    config = {'model': 'lab/scripted', 'small_model': 'lab/scripted', 'default_agent': 'coordinator',
              'enabled_providers': ['lab'], 'share': 'disabled', 'autoupdate': False, 'username': 'lab',
              'snapshot': False, 'lsp': False, 'formatter': False, 'subagent_depth': 1,
              'permission': {'*': 'deny'}, 'agent': roles(case),
              'provider': {'lab': {'npm': '@ai-sdk/openai-compatible', 'name': 'Scripted fixture',
                 'options': {'baseURL': f'http://127.0.0.1:{provider.server_port}/v1', 'apiKey': 'lab'},
                 'models': {'scripted': {'name': 'No inference', 'limit': {'context': 32768, 'output': 4096}}}}}}
    write_json(root / 'opencode.json', config)
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'LANG', 'LC_ALL'}}
    env.update({'OPENCODE_CONFIG': str(root / 'opencode.json'), 'OPENCODE_CONFIG_DIR': str(root / 'config'),
                'OPENCODE_TEST_HOME': str(root / 'home'), 'HOME': str(root / 'home'), 'USERPROFILE': str(root / 'home'),
                'TEMP': str(root / 'temp'), 'TMP': str(root / 'temp'), 'OPENCODE_DISABLE_AUTOUPDATE': 'true',
                'OPENCODE_DISABLE_MODELS_FETCH': 'true', 'OPENCODE_DISABLE_PROJECT_CONFIG': 'true', 'OPENCODE_PURE': 'true',
                'XDG_DATA_HOME': str(root / 'data'), 'XDG_CONFIG_HOME': str(root / 'config'),
                'XDG_CACHE_HOME': str(root / 'cache'), 'XDG_STATE_HOME': str(root / 'state'), 'NO_COLOR': '1'})
    write_json(root / 'environment-keys.json', sorted(env))
    server = None
    out = err = None
    try:
        for stem, args in (('config', ['config']), ('parent', ['agent', 'coordinator']), ('child', ['agent', 'worker'])):
            result = execute([str(cli), 'debug', *args, '--pure'], root, 'resolved-' + stem, workspace, env, 60)
            if result.returncode:
                raise RuntimeError('configuration capture failed')
        out = (root / 'server.stdout.txt').open('w', encoding='utf-8')
        err = (root / 'server.stderr.txt').open('w', encoding='utf-8')
        command = [str(cli), '--print-logs', '--log-level', 'INFO', 'serve', '--pure', '--hostname', '127.0.0.1', '--port', '0']
        write_json(root / 'server-command.json', command)
        server = subprocess.Popen(command, cwd=workspace, env=env, stdout=out, stderr=err,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        import re
        url = None
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            match = re.search(r'http://127\.0\.0\.1:\d+', (root / 'server.stdout.txt').read_text(encoding='utf-8'))
            if match:
                url = match.group(0)
                break
            if server.poll() is not None:
                raise RuntimeError('server exited during startup')
            time.sleep(.1)
        if not url:
            raise RuntimeError('server startup timeout')
        def api(method, path, payload=None):
            request = urllib.request.Request(url + path, method=method,
                 headers={'Content-Type': 'application/json'},
                 data=None if payload is None else json.dumps(payload).encode())
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        create = {'title': 'Synthetic boundary ' + case, 'agent': 'coordinator',
                  'model': {'providerID': 'lab', 'id': 'scripted'}, 'permission': session_rules(case)}
        write_json(root / 'session-create-input.json', create)
        created = api('POST', '/session', create)
        write_json(root / 'session-created.json', created)
        identities['parent'] = created['id']
        write_json(root / 'identities.json', identities)
        snapshot(workspace, root / 'before')
        execute([str(node), '--test', 'labels.test.mjs'], root, 'test-before', workspace, env, 30)
        prompt = DIRECT_PROMPT if case == 'parent-role-direct' else PROMPT
        result = execute([str(cli), 'run', '--pure', '--attach', url, '--session', identities['parent'],
                          '--format', 'json', '--model', 'lab/scripted', '--agent', 'coordinator', '--', prompt],
                         root, 'cli', workspace, env, 150)
        snapshot(workspace, root / 'after')
        execute([str(node), '--test', 'labels.test.mjs'], root, 'test-after', workspace, env, 30)
        write_json(root / 'children.json', api('GET', '/session/' + identities['parent'] + '/children'))
        for owner, sid in identities.items():
            write_json(root / ('export-' + owner + '.json'), {'info': api('GET', '/session/' + sid),
                       'messages': api('GET', '/session/' + sid + '/message')})
        if errors or result.returncode:
            raise RuntimeError('provider or CLI failure; inspect private capture')
        print(case + ': captured ' + str(count) + ' requests; verify separately.', flush=True)
    finally:
        if server is not None:
            server.terminate()
            server.wait(timeout=15)
        if out:
            out.close()
        if err:
            err.close()
        provider.shutdown()
        provider.server_close()
        thread.join(timeout=5)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', required=True, type=Path)
    parser.add_argument('--node', type=Path, default=shutil.which('node'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--case', choices=CASES, action='append')
    args = parser.parse_args()
    if platform.system() != 'Windows':
        parser.error('Fresh execution currently documented for Windows; offline checks are portable.')
    cli, node = args.opencode.resolve(), Path(args.node).resolve()
    if sha(cli.read_bytes()) != BINARY_SHA256:
        parser.error('Expected official v1.18.30 Windows x64 binary digest')
    if args.output.resolve().is_relative_to(LAB.parents[4]):
        parser.error('Keep private capture outside checkout')
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='boundary-', dir=args.output.resolve()))
    checkout = LAB.parents[4]
    revision = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    changes = subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain', '--untracked-files=all', '--', str(LAB)], text=True)
    write_json(root / 'run.json', {'schema_version': 1, 'release': 'v1.18.30', 'commit': PIN,
        'binary_sha256': BINARY_SHA256, 'platform': platform.system(), 'architecture': platform.machine(),
        'lab_revision': revision, 'lab_dirty': bool(changes), 'runner_sha256': sha(Path(__file__).read_bytes()),
        'cases': args.case or list(CASES), 'entrypoint': 'serve + API session.create + run --attach --session',
        'evidence_class': 'OBSERVED_WITH_SCRIPTED_PROVIDER', 'model_inference': False})
    print('Private capture: ' + str(root), flush=True)
    for case in args.case or CASES:
        run_case(root / case, case, cli, node)

if __name__ == '__main__':
    main()
