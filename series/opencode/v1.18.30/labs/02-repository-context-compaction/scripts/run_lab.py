"""Real OpenCode, synthetic files and a scripted loopback provider. No inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MARKERS = ['GLOBAL_RULE', 'ROOT_RULE', 'FALLBACK_RULE', 'NESTED_RULE',
           'CONFIG_RULE', 'ATTACHED_NOTE', 'UNREAD_SECRET', 'OLD_FILE',
           'OLD_END', 'NEW_FILE', 'TAIL_FILE', 'OLD_REQUEST', 'TAIL_REQUEST',
           'REREAD_REQUEST', 'SUMMARY_NOTE']
PREFIX = 'LAB_P2_'
SUMMARY = PREFIX + 'SUMMARY_NOTE: Earlier inspection completed. Re-read mutable files before continuing.'
OLD = '// ' + PREFIX + 'OLD_FILE\n' + '// filler for summary input clipping\n' * 100 + '// ' + PREFIX + 'OLD_END\n'
NEW = '// ' + PREFIX + 'NEW_FILE\nexport const slug = s => s.trim().toLowerCase();\n'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def marks(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return [m for m in MARKERS if PREFIX + m in text]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')


def run_case(root, cli, mode):
    case = root / mode
    workspace = case / 'workspace'
    (workspace / 'src').mkdir(parents=True)
    config_dir = case / 'config'
    (config_dir / 'opencode').mkdir(parents=True)
    fixtures = {'AGENTS.md': PREFIX + 'ROOT_RULE: Verify current files.\n',
                'CLAUDE.md': PREFIX + 'FALLBACK_RULE\n',
                'src/AGENTS.md': PREFIX + 'NESTED_RULE: Use the slug test command.\n',
                'src/slug.mjs': OLD, 'recent.txt': PREFIX + 'TAIL_FILE\n',
                'attached.txt': PREFIX + 'ATTACHED_NOTE\n',
                'unread.txt': PREFIX + 'UNREAD_SECRET\n',
                'extra-rules.txt': PREFIX + 'CONFIG_RULE\n'}
    for name, content in fixtures.items():
        (workspace / name).write_bytes(content.encode())
    (config_dir / 'opencode' / 'AGENTS.md').write_text(PREFIX + 'GLOBAL_RULE\n', encoding='utf-8')
    # A Git root bounds upward discovery; no commit or user Git configuration needed.
    subprocess.run(['git', 'init', '--quiet', str(workspace)], check=True, capture_output=True)
    requests, emitted, calls = [], [], []
    stage, ordinary = 0, 0

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            nonlocal ordinary
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            index = len(requests) + 1
            write_json(case / f'request-{index:02}.json', payload)
            messages = payload.get('messages', [])
            tools = payload.get('tools', [])
            kind = 'ordinary' if tools else 'auxiliary'
            # Compaction has no tools and includes the serialized old conversation.
            if not tools and PREFIX + 'OLD_REQUEST' in json.dumps(messages):
                kind = 'compaction'
            summary = {'index': index, 'stage': stage, 'kind': kind,
                       'stream': payload.get('stream', False),
                       'messages': [{'role': m.get('role'), 'markers': marks(m.get('content', '')),
                                     'tool_call_id': m.get('tool_call_id'),
                                     'tool_calls': [t['id'] for t in m.get('tool_calls', [])],
                                     'content_sha256': sha((m['content'] if isinstance(m.get('content'), str) else json.dumps(m.get('content'), sort_keys=True)).encode()),
                                     'content_chars': len(json.dumps(m.get('content')))} for m in messages],
                       'file_sha256_at_request': sha((workspace / 'src/slug.mjs').read_bytes()),
                       'file_markers_at_request': marks((workspace / 'src/slug.mjs').read_text())}
            requests.append(summary)
            text, tool, usage = 'Synthetic acknowledgement.', None, 10
            if kind == 'compaction':
                text = SUMMARY
            elif kind == 'ordinary':
                ordinary += 1
                if ordinary == 1:
                    name = 'recent.txt' if stage == 2 else 'src/slug.mjs'
                    tool = {'index': 0, 'id': f'lab_read_{stage}', 'type': 'function',
                            'function': {'name': 'read', 'arguments': json.dumps({'filePath': str(workspace / name)})}}
                    emitted.append({'stage': stage, 'id': tool['id'], 'tool': 'read', 'file': name})
                elif stage == 2 and ordinary == 2:
                    # Identical provider-reported usage in both cases, not measured tokenizer usage.
                    usage = 31000
            summary['response_usage'] = usage
            summary['response_tool_id'] = tool['id'] if tool else None
            summary['response_markers'] = marks(text) if not tool else []
            message = {'role': 'assistant', 'content': text}
            reason = 'stop'
            if tool:
                message = {'role': 'assistant', 'tool_calls': [tool]}
                reason = 'tool_calls'
            token_usage = {'prompt_tokens': usage, 'completion_tokens': 1, 'total_tokens': usage + 1}
            if not payload.get('stream'):
                data = json.dumps({'id': 'lab', 'object': 'chat.completion', 'model': 'scripted',
                                   'choices': [{'index': 0, 'message': message, 'finish_reason': reason}],
                                   'usage': token_usage}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Connection', 'close')
            self.end_headers()
            for delta, finish in [(message, None), ({}, reason)]:
                chunk = {'id': 'lab', 'object': 'chat.completion.chunk', 'model': 'scripted',
                         'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                if finish:
                    chunk['usage'] = token_usage
                self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()

    server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = {'model': 'lab/scripted', 'small_model': 'lab/scripted',
              'enabled_providers': ['lab'], 'share': 'disabled', 'autoupdate': False,
              'snapshot': False, 'lsp': False,
              'instructions': ['extra-rules.txt'],
              'permission': {'*': 'deny', 'read': 'allow'},
              'compaction': {'auto': mode == 'compact', 'prune': False,
                             'tail_turns': 1, 'preserve_recent_tokens': 8000},
              'provider': {'lab': {'npm': '@ai-sdk/openai-compatible',
                                  'name': 'Scripted fixture',
                                  'options': {'baseURL': f'http://127.0.0.1:{server.server_port}/v1', 'apiKey': 'lab'},
                                  'models': {'scripted': {'name': 'No inference',
                                                         'limit': {'context': 32768, 'output': 4096}}}}}}
    write_json(case / 'opencode.json', config)
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP',
        'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'LANG', 'LC_ALL'}}
    env.update({'OPENCODE_CONFIG': str(case / 'opencode.json'),
                'OPENCODE_CONFIG_DIR': str(config_dir / 'opencode'),
                'OPENCODE_TEST_HOME': str(case / 'home'),
                'HOME': str(case / 'home'), 'USERPROFILE': str(case / 'home'),
                'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'OPENCODE_DISABLE_MODELS_FETCH': 'true',
                'OPENCODE_PURE': 'true', 'XDG_DATA_HOME': str(case / 'data'),
                'XDG_CONFIG_HOME': str(config_dir), 'XDG_CACHE_HOME': str(case / 'cache'),
                'XDG_STATE_HOME': str(case / 'state'), 'NO_COLOR': '1'})
    session_id = None
    try:
        for stage in range(1, 4):
            ordinary = 0
            if stage == 2:
                (workspace / 'src/slug.mjs').write_bytes(NEW.encode())
            prompt = [f'Inspect src/slug.mjs. {PREFIX}OLD_REQUEST',
                      f'Inspect recent.txt. {PREFIX}TAIL_REQUEST',
                      f'Re-read src/slug.mjs. {PREFIX}REREAD_REQUEST'][stage - 1]
            command = [str(cli), 'run', '--pure', '--format', 'json', '--model', 'lab/scripted']
            if session_id:
                command += ['--session', session_id]
            else:
                command += ['--title', 'Synthetic context boundary', '--file', 'attached.txt']
            command += ['--', prompt]
            result = subprocess.run(command, cwd=workspace, env=env, capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=180)
            (case / f'cli-{stage}.stdout.jsonl').write_text(result.stdout, encoding='utf-8')
            (case / f'cli-{stage}.stderr.txt').write_text(result.stderr, encoding='utf-8')
            events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
            ids = {e['sessionID'] for e in events if 'sessionID' in e}
            if len(ids) != 1 or (session_id and ids != {session_id}):
                raise RuntimeError(f'Session evidence missing or changed: {case}, stage {stage}')
            session_id = ids.pop()
            calls.append({'stage': stage, 'exit': result.returncode, 'session_id': session_id,
                          'errors': [e.get('error') for e in events if e.get('type') == 'error']})
            export = subprocess.run([str(cli), 'export', session_id], cwd=workspace, env=env,
                                    capture_output=True, text=True, encoding='utf-8', timeout=60)
            (case / f'export-{stage}.json').write_text(export.stdout, encoding='utf-8')
            if export.returncode:
                raise RuntimeError(f'Export failed: {case}, stage {stage}')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    durable = json.loads((case / 'export-3.json').read_text(encoding='utf-8'))
    messages = []
    for m in durable['messages']:
        info = m['info']
        parts = []
        for p in m['parts']:
            record = {'id': p['id'], 'type': p['type']}
            if p['type'] == 'text':
                record.update(markers=marks(p['text']), synthetic=p.get('synthetic', False))
            if p['type'] == 'compaction':
                record.update(auto=p['auto'], tail_start_id=p.get('tail_start_id'))
            if p['type'] == 'tool':
                s = p['state']
                record.update(tool=p['tool'], call_id=p['callID'], status=s['status'],
                              output_markers=marks(s.get('output', '')),
                              output_sha256=sha(s.get('output', '').encode()),
                              compacted=bool(s.get('time', {}).get('compacted')),
                              loaded=[Path(x).relative_to(workspace).as_posix() for x in s.get('metadata', {}).get('loaded', [])])
            parts.append(record)
        messages.append({'id': info['id'], 'role': info['role'], 'parent_id': info.get('parentID'),
                         'summary': info.get('summary', False) if info['role'] == 'assistant' else False,
                         'finish': info.get('finish'), 'tokens': info.get('tokens'), 'parts': parts})
    current = {name: {'sha256': sha((workspace / name).read_bytes()),
                      'markers': marks((workspace / name).read_text())} for name in fixtures}
    return {'mode': mode, 'session_id': session_id,
            'config': {'auto': mode == 'compact', 'prune': False,
                                   'tail_turns': 1, 'preserve_recent_tokens': 8000},
            'calls': calls, 'requests': requests, 'emitted': emitted,
            'messages': messages, 'current_files': current}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path, help='Private directory outside the checkout')
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(Path(__file__).resolve().parents[6]):
        parser.error('Raw evidence output must be outside this checkout.')
    cli = args.opencode.resolve()
    version = subprocess.run([str(cli), '--version'], capture_output=True, text=True, timeout=30).stdout.strip()
    if version != '1.18.30':
        parser.error(f'Expected OpenCode 1.18.30, found {version}')
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='context-', dir=args.output.resolve()))
    print(root, flush=True)
    report = {'schema_version': 1, 'release': version,
              'commit': '3104c1428ec91f809e5ab86631300de41eb6952e',
              'platform': platform.system(), 'architecture': platform.machine(),
              'binary_sha256': sha(cli.read_bytes()),
              'evidence_class': 'OBSERVED_WITH_SCRIPTED_PROVIDER',
              'cases': [run_case(root, cli, mode) for mode in ['no_compact', 'compact']]}
    write_json(root / 'receipt.json', report)
    from verify_reference import verify
    errors = verify(report)
    print(json.dumps({'errors': errors, 'passed': not errors}))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
