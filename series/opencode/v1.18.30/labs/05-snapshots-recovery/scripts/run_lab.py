"""Real Windows OpenCode recovery with scripted loopback responses, no inference.

Creates new disposable directories only. Raw captures never belong in public Git.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contract import (BINARY_SHA256, CALLS, CASES, CONTINUATION, FILES, FINAL, LAB,
                      PIN, PROMPT, fixture, roles, sha)

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def execute(command, root, stem, workspace, env, timeout=120):
    try:
        result = subprocess.run(command, cwd=workspace, env=env, capture_output=True,
                                timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    except subprocess.TimeoutExpired as exc:
        (root / (stem + '.stdout.txt')).write_bytes(exc.stdout or b'')
        (root / (stem + '.stderr.txt')).write_bytes(exc.stderr or b'')
        write_json(root / (stem + '.process.json'), {'command': command, 'exit': None,
                   'timed_out': True, 'timeout_seconds': timeout})
        raise
    (root / (stem + '.stdout.txt')).write_bytes(result.stdout)
    (root / (stem + '.stderr.txt')).write_bytes(result.stderr)
    write_json(root / (stem + '.process.json'), {'command': command, 'exit': result.returncode})
    return result

def snapshot(workspace, destination):
    destination.mkdir()
    manifest = {}
    for item in sorted(workspace.rglob('*')):
        rel = item.relative_to(workspace)
        if '.git' in rel.parts or not item.is_file():
            continue
        data = item.read_bytes()
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        manifest[rel.as_posix()] = {'sha256': sha(data), 'bytes': len(data)}
    write_json(destination / 'manifest.json', manifest)

def run_case(root, case, cli, node, continuation):
    root.mkdir()
    workspace = root / 'workspace'
    workspace.mkdir()
    for name in FILES:
        (workspace / name).write_bytes(fixture(name))
    for name in ('home', 'config', 'data', 'cache', 'state', 'temp', 'hooks'):
        (root / name).mkdir()
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'PROCESSOR_ARCHITECTURE',
        'NUMBER_OF_PROCESSORS', 'LANG', 'LC_ALL'}}
    env.update({'OPENCODE_CONFIG': str(root / 'opencode.json'), 'OPENCODE_CONFIG_DIR': str(root / 'config'),
        'OPENCODE_TEST_HOME': str(root / 'home'), 'HOME': str(root / 'home'), 'USERPROFILE': str(root / 'home'),
        'TEMP': str(root / 'temp'), 'TMP': str(root / 'temp'), 'OPENCODE_DISABLE_AUTOUPDATE': 'true',
        'OPENCODE_DISABLE_MODELS_FETCH': 'true', 'OPENCODE_DISABLE_PROJECT_CONFIG': 'true', 'OPENCODE_PURE': 'true',
        'XDG_DATA_HOME': str(root / 'data'), 'XDG_CONFIG_HOME': str(root / 'config'),
        'XDG_CACHE_HOME': str(root / 'cache'), 'XDG_STATE_HOME': str(root / 'state'), 'NO_COLOR': '1',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(root / 'home' / 'empty-gitconfig')})
    (root / 'home' / 'empty-gitconfig').write_text('', encoding='utf-8')
    write_json(root / 'environment-keys.json', sorted(env))
    setup = [['git', '-c', 'init.templateDir=', 'init', '--quiet'],
             ['git', 'add', '--', *FILES],
             ['git', '-c', 'core.hooksPath=' + str(root / 'hooks'), '-c', 'commit.gpgsign=false',
              '-c', 'user.name=Synthetic Lab', '-c', 'user.email=lab@example.invalid', 'commit', '--quiet', '-m', 'Fixture'],
             ['git', 'rev-parse', '--show-toplevel'], ['git', 'status', '--porcelain']]
    for index, command in enumerate(setup):
        if execute(command, root, f'git-setup-{index}', workspace, env).returncode:
            raise RuntimeError('fixture Git initialization failed')
    count, errors, sequence, trees = 0, [], [], {}
    lock = threading.Lock()
    sid = None
    def event(kind, **details):
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
                if index > 12 or self.path != '/v1/chat/completions':
                    raise ValueError('unexpected provider path or count')
                headers = {k.lower(): v for k, v in self.headers.items()
                           if k.lower() in ('x-session-id', 'x-session-affinity', 'x-parent-session-id')}
                write_json(root / f'request-{index:02}.json', {'path': self.path, 'headers': headers, 'body': body})
                event('provider_request', request=index)
                available = {t['function']['name'] for t in body.get('tools', [])}
                replies = [m for m in body.get('messages', []) if m['role'] == 'tool']
                main = bool(available)
                call = None
                if main:
                    if headers.get('x-session-id') != sid:
                        raise ValueError('wrong provider session')
                    if [r['tool_call_id'] for r in replies] != [c[0] for c in CALLS[:len(replies)]]:
                        raise ValueError('unexpected tool history')
                    call = CALLS[len(replies)] if len(replies) < len(CALLS) else None
                message = {'role': 'assistant', 'content': FINAL if main else 'Synthetic recovery task'}
                finish = 'stop'
                if call:
                    ident, name, args = call
                    if name not in available:
                        raise ValueError('tool was not advertised')
                    message = {'role': 'assistant', 'tool_calls': [{'index': 0, 'id': ident, 'type': 'function',
                        'function': {'name': name, 'arguments': json.dumps(args)}}]}
                    finish = 'tool_calls'
                write_json(root / f'response-{index:02}.json', {'kind': 'main' if main else 'auxiliary',
                            'message': message, 'finish_reason': finish})
                event('provider_response', request=index, finish=finish)
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
    config = {'model': 'lab/scripted', 'small_model': 'lab/scripted', 'default_agent': 'builder',
        'enabled_providers': ['lab'], 'share': 'disabled', 'autoupdate': False, 'username': 'lab',
        'snapshot': True, 'lsp': False, 'formatter': False, 'permission': {'*': 'deny'}, 'agent': roles(),
        'provider': {'lab': {'npm': '@ai-sdk/openai-compatible', 'name': 'Scripted fixture',
            'options': {'baseURL': f'http://127.0.0.1:{provider.server_port}/v1', 'apiKey': 'lab'},
            'models': {'scripted': {'name': 'No inference', 'limit': {'context': 32768, 'output': 4096}}}}}}
    write_json(root / 'opencode.json', config)
    server = out = err = None
    try:
        for stem, command in [('version', [str(cli), '--version']), ('node-version', [str(node), '--version']),
              ('git-version', ['git', '--version']), ('resolved-config', [str(cli), 'debug', 'config', '--pure']),
              ('resolved-agent', [str(cli), 'debug', 'agent', 'builder', '--pure'])]:
            if execute(command, root, stem, workspace, env).returncode:
                raise RuntimeError(stem + ' capture failed')
        out = (root / 'server.stdout.txt').open('w', encoding='utf-8')
        err = (root / 'server.stderr.txt').open('w', encoding='utf-8')
        command = [str(cli), '--print-logs', '--log-level', 'INFO', 'serve', '--pure', '--hostname', '127.0.0.1', '--port', '0']
        write_json(root / 'server-command.json', command)
        server = subprocess.Popen(command, cwd=workspace, env=env, stdout=out, stderr=err,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
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

        def api(method, path, stem, payload=None):
            write_json(root / (stem + '.request.json'), {'method': method, 'url': url + path, 'payload': payload})
            event('api_request', stem=stem)
            request = urllib.request.Request(url + path, method=method, headers={'Content-Type': 'application/json'},
                                            data=None if payload is None else json.dumps(payload).encode())
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read()
                (root / (stem + '.response.json')).write_bytes(raw)
                write_json(root / (stem + '.http.json'), {'status': response.status})
                result = json.loads(raw)
            event('api_return', stem=stem)
            return result

        def capture_trees(info, messages):
            hashes = {p.get('snapshot') for m in messages for p in m['parts'] if p.get('snapshot')}
            hashes.update(p['hash'] for m in messages for p in m['parts'] if p['type'] == 'patch')
            if info.get('revert', {}).get('snapshot'):
                hashes.add(info['revert']['snapshot'])
            for tree_hash in sorted(hashes):
                if tree_hash in trees:
                    continue
                if not re.fullmatch('[0-9a-f]{40}', tree_hash):
                    raise RuntimeError('unexpected snapshot reference')
                candidates = [p.parent for p in (root / 'data').rglob('HEAD') if 'snapshot' in p.parts]
                matched = []
                for index, gitdir in enumerate(candidates):
                    cmd = ['git', '--git-dir=' + str(gitdir), 'cat-file', '-t', tree_hash]
                    result = execute(cmd, root, f'tree-{tree_hash}-probe-{index}', workspace, env, 30)
                    if result.returncode == 0 and result.stdout.strip() == b'tree':
                        matched.append(gitdir)
                if len(matched) != 1:
                    raise RuntimeError('snapshot tree is missing or ambiguous')
                gitdir = matched[0]
                reads = 0
                def git_read(*args):
                    nonlocal reads
                    reads += 1
                    result = execute(['git', '--git-dir=' + str(gitdir), *args], root,
                                     f'tree-{tree_hash}-read-{reads}', workspace, env, 30)
                    result.check_returncode()
                    return result.stdout
                raw_tree = git_read('cat-file', 'tree', tree_hash)
                listing = git_read('ls-tree', '-r', '-z', tree_hash)
                blobs = {}
                for entry in listing.split(b'\0'):
                    if not entry:
                        continue
                    meta, path = entry.split(b'\t', 1)
                    mode, kind, blob = meta.decode().split()
                    if kind != 'blob':
                        raise RuntimeError('unexpected fixture tree object')
                    data = git_read('cat-file', 'blob', blob)
                    blobs[path.decode()] = {'mode': mode, 'object': blob, 'base64': base64.b64encode(data).decode()}
                trees[tree_hash] = {'gitdir': str(gitdir), 'object_base64': base64.b64encode(raw_tree).decode(), 'files': blobs}
                write_json(root / 'snapshot-trees.json', trees)

        created = api('POST', '/session', 'session-create', {'title': 'Synthetic recovery ' + case,
            'agent': 'builder', 'model': {'providerID': 'lab', 'id': 'scripted'}})
        sid = created['id']
        write_json(root / 'identity.json', {'session': sid, 'workspace': str(workspace)})
        def checkpoint(stage):
            status = api('GET', '/session/status', stage + '-status')
            if sid in status and status[sid]['type'] != 'idle':
                raise RuntimeError('session is not idle at checkpoint')
            info = api('GET', '/session/' + sid, stage + '-session')
            messages = api('GET', '/session/' + sid + '/message', stage + '-messages')
            api('GET', '/session/' + sid + '/diff', stage + '-diff')
            capture_trees(info, messages)
            snapshot(workspace, root / stage)
            execute([str(node), '--test', 'labels.test.mjs'], root, stage + '-test', workspace, env, 30)
            execute([str(node), '--input-type=module', '-e',
                     "import {displayMode} from './labels.mjs'; console.log(JSON.stringify({displayMode}));"],
                    root, stage + '-value', workspace, env, 30)
            event('checkpoint', stage=stage, provider_requests=count)
            return info, messages

        checkpoint('r0')
        event('coding_start')
        result = execute([str(cli), 'run', '--pure', '--attach', url, '--session', sid,
            '--format', 'json', '--model', 'lab/scripted', '--agent', 'builder', '--', PROMPT],
            root, 'cli', workspace, env, 180)
        event('coding_return', exit=result.returncode)
        if result.returncode or errors:
            raise RuntimeError('coding request or provider failed')
        _, messages = checkpoint('r1')
        users = [m for m in messages if m['info']['role'] == 'user']
        if len(users) != 1:
            raise RuntimeError('unexpected coding message count')
        target = users[0]['info']['id']
        (workspace / 'notes.txt').write_bytes(b'Independent note: later work.\n')
        event('external_write', path='notes.txt')
        if case == 'same-file':
            helper = workspace / 'labels.mjs'
            before = helper.read_bytes()
            if before.count(b"'compact'") != 1:
                raise RuntimeError('unexpected setting before later edit')
            helper.write_bytes(before.replace(b"'compact'", b"'expanded'"))
            event('external_write', path='labels.mjs')
        checkpoint('r2')
        api('POST', '/session/' + sid + '/revert', 'first-revert', {'messageID': target})
        checkpoint('r3')
        api('POST', '/session/' + sid + '/unrevert', 'unrevert', {})
        checkpoint('r4')
        event('primary_complete')
        if continuation and case == 'same-file':
            api('POST', '/session/' + sid + '/revert', 'continuation-revert', {'messageID': target})
            checkpoint('c0')
            api('POST', '/session/' + sid + '/message', 'continuation-message',
                {'noReply': True, 'parts': [{'type': 'text', 'text': CONTINUATION}]})
            checkpoint('c1')
            event('continuation_complete')
        if errors:
            raise RuntimeError('provider errors occurred')
        print(case + ': captured; run the independent verifier.', flush=True)
    finally:
        try:
            if server is not None and server.poll() is None:
                server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
        finally:
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
    parser.add_argument('--skip-continuation', action='store_true')
    args = parser.parse_args()
    if platform.system() != 'Windows':
        parser.error('Runtime execution is documented on Windows; offline checks are portable.')
    cli, node = args.opencode.resolve(), Path(args.node).resolve()
    if sha(cli.read_bytes()) != BINARY_SHA256:
        parser.error('Expected official v1.18.30 Windows x64 executable digest')
    checkout = LAB.parents[4]
    if args.output.resolve().is_relative_to(checkout):
        parser.error('Keep private captures outside the checkout')
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='recovery-', dir=args.output.resolve()))
    print('Private capture: ' + str(root), flush=True)
    revision_result = execute(['git', '-C', str(checkout), 'rev-parse', 'HEAD'],
                              root, 'lab-revision', checkout, os.environ.copy(), 30)
    revision_result.check_returncode()
    revision = revision_result.stdout.decode().strip()
    changes_result = execute(['git', '-C', str(checkout), 'status', '--porcelain', '--untracked-files=all', '--', str(LAB)],
                             root, 'lab-changes', checkout, os.environ.copy(), 30)
    changes_result.check_returncode()
    changes = changes_result.stdout.decode()
    write_json(root / 'run.json', {'schema_version': 1, 'release': 'v1.18.30', 'commit': PIN,
        'binary_sha256': BINARY_SHA256, 'platform': platform.system(), 'architecture': platform.machine(),
        'lab_revision': revision, 'lab_dirty': bool(changes), 'runner_sha256': sha(Path(__file__).read_bytes()),
        'cases': list(CASES), 'evidence_class': 'OBSERVED_WITH_SCRIPTED_PROVIDER', 'model_inference': False,
        'continuation': not args.skip_continuation})
    for case in CASES:
        run_case(root / case, case, cli, node, not args.skip_continuation)

if __name__ == '__main__':
    main()
