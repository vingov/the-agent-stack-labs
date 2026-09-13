"""Exercise the real OpenCode CLI with a scripted local provider, never real inference."""
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
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from verify_reference import verify_report


BUGGY = "export const slug = s => s.trim().toLowerCase().replaceAll(' ', '-');\n"
TEST = """import { test } from 'node:test';
import assert from 'node:assert/strict';
import { slug } from './slug.mjs';
test('single space', () => assert.equal(slug('Hello World'), 'hello-world'));
test('repeated whitespace', () => assert.equal(slug(' Hello  World '), 'hello-world'));
test('tab', () => assert.equal(slug('Hello\\tWorld'), 'hello-world'));
"""
FINAL = "The whitespace bug is fixed and the tests pass."


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_case(root, cli, node, mode):
    case = root / mode
    workspace = case / 'workspace'
    workspace.mkdir(parents=True)
    (workspace / 'slug.mjs').write_text(BUGGY, encoding='utf-8')
    (workspace / 'slug.test.mjs').write_text(TEST, encoding='utf-8')
    requests = []
    emitted = []

    class Provider(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            messages = payload.get('messages', [])
            tools = payload.get('tools', [])
            tool_results = [m for m in messages if m.get('role') == 'tool']
            requests.append({
                'path': self.path,
                'roles': [m.get('role') for m in messages],
                'tool_result_count': len(tool_results),
                'tool_result_ids': [m.get('tool_call_id') for m in tool_results],
                'advertised_tools': [t.get('function', {}).get('name') for t in tools],
                'stream': payload.get('stream', False),
            })
            tool = None
            arguments = None
            # Auxiliary requests without tools receive a harmless synthetic title.
            if tools and mode == 'tool_loop':
                step = len(tool_results)
                if step == 0:
                    tool, arguments = 'read', {'filePath': str(workspace / 'slug.mjs')}
                elif step == 1:
                    tool, arguments = 'edit', {
                        'filePath': str(workspace / 'slug.mjs'),
                        'oldString': "replaceAll(' ', '-')",
                        'newString': "replace(/\\s+/g, '-')",
                    }
                elif step == 2:
                    tool, arguments = 'bash', {
                        'command': 'node --test slug.test.mjs',
                        'description': 'Run the synthetic slug tests',
                    }
            text = FINAL if tools else 'Synthetic slug task'
            call_id = f'lab_call_{len(emitted)}'
            if tool:
                emitted.append({'tool': tool, 'id': call_id})
            if not payload.get('stream'):
                body = {'id': 'lab', 'object': 'chat.completion', 'created': int(time.time()),
                        'model': 'scripted', 'choices': [{'index': 0, 'message': {
                            'role': 'assistant', 'content': text}, 'finish_reason': 'stop'}],
                        'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2}}
                data = json.dumps(body).encode()
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
            delta = {'role': 'assistant', 'content': text}
            reason = 'stop'
            if tool:
                delta = {'role': 'assistant', 'tool_calls': [{
                    'index': 0, 'id': call_id, 'type': 'function',
                    'function': {'name': tool, 'arguments': json.dumps(arguments)},
                }]}
                reason = 'tool_calls'
            for part, finish in [(delta, None), ({}, reason)]:
                event = {'id': 'lab', 'object': 'chat.completion.chunk', 'created': int(time.time()),
                         'model': 'scripted', 'choices': [{'index': 0, 'delta': part, 'finish_reason': finish}]}
                self.wfile.write(('data: ' + json.dumps(event) + '\n\n').encode())
            self.wfile.write(b'data: [DONE]\n\n')
            self.wfile.flush()

    server = ThreadingHTTPServer(('127.0.0.1', 0), Provider)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    config = {
        'model': 'lab/scripted', 'small_model': 'lab/scripted',
        'enabled_providers': ['lab'], 'share': 'disabled', 'autoupdate': False,
        'permission': {'*': 'deny', 'read': 'allow', 'edit': 'allow',
                       'bash': {'*': 'deny', 'node --test slug.test.mjs': 'allow'}},
        'provider': {'lab': {'npm': '@ai-sdk/openai-compatible', 'name': 'Scripted local lab',
            'options': {'baseURL': f'http://127.0.0.1:{server.server_port}/v1',
                        'apiKey': 'lab'},
            'models': {'scripted': {'name': 'Scripted fixture, no inference',
                'limit': {'context': 32768, 'output': 4096}}}}},
    }
    config_path = case / 'opencode.json'
    config_path.write_text(json.dumps(config), encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k.upper() in {
        'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP',
        'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS', 'LANG', 'LC_ALL'}}
    env.update({
        'OPENCODE_CONFIG': str(config_path), 'OPENCODE_CONFIG_DIR': str(case / 'config'),
        'OPENCODE_TEST_HOME': str(case / 'home'),
        'OPENCODE_DISABLE_AUTOUPDATE': 'true', 'OPENCODE_DISABLE_MODELS_FETCH': 'true',
        'OPENCODE_DISABLE_PROJECT_CONFIG': 'true', 'OPENCODE_PURE': 'true',
        'XDG_DATA_HOME': str(case / 'data'), 'XDG_CONFIG_HOME': str(case / 'config'),
        'XDG_CACHE_HOME': str(case / 'cache'), 'XDG_STATE_HOME': str(case / 'state'),
        'NO_COLOR': '1',
    })
    env['PATH'] = str(Path(node).parent) + os.pathsep + env.get('PATH', '')
    before = subprocess.run([node, '--test', 'slug.test.mjs'], cwd=workspace, env=env,
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    before_hash = digest(workspace / 'slug.mjs')
    test_hash = digest(workspace / 'slug.test.mjs')
    started = time.monotonic()
    try:
        result = subprocess.run([str(cli), 'run', '--pure', '--format', 'json',
                                 '--model', 'lab/scripted', '--title', 'Synthetic slug boundary',
                                 'Fix repeated whitespace in slug.mjs and run the tests.'],
                                cwd=workspace, env=env, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=180)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    after = subprocess.run([node, '--test', 'slug.test.mjs'], cwd=workspace, env=env,
                           capture_output=True, text=True, encoding='utf-8', timeout=30)
    (case / 'cli.stdout.jsonl').write_text(result.stdout, encoding='utf-8')
    (case / 'cli.stderr.txt').write_text(result.stderr, encoding='utf-8')
    (case / 'verifier-before.txt').write_text(before.stdout + before.stderr, encoding='utf-8')
    (case / 'verifier-after.txt').write_text(after.stdout + after.stderr, encoding='utf-8')
    (case / 'provider-summary.json').write_text(json.dumps(requests, indent=2), encoding='utf-8')
    events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    observed_tools = [e['part'] for e in events if e.get('type') == 'tool_use']
    summary = {
        'case': mode, 'evidence_class': 'OBSERVED_WITH_SCRIPTED_PROVIDER',
        'cli_exit': result.returncode, 'baseline_test_exit': before.returncode,
        'independent_test_exit': after.returncode,
        'file_changed': before_hash != digest(workspace / 'slug.mjs'),
        'test_file_unchanged': test_hash == digest(workspace / 'slug.test.mjs'),
        'before_sha256': before_hash, 'after_sha256': digest(workspace / 'slug.mjs'),
        'test_before_sha256': test_hash, 'test_after_sha256': digest(workspace / 'slug.test.mjs'),
        'provider_requests': len(requests), 'tool_calls_emitted': emitted,
        'tools_observed': [{'tool': p['tool'], 'call_id': p['callID'],
                            'status': p['state']['status'],
                            'exit': p['state'].get('metadata', {}).get('exit')}
                           for p in observed_tools],
        'session_count': len({e['sessionID'] for e in events if 'sessionID' in e}),
        'step_finish_reasons': [e['part']['reason'] for e in events if e.get('type') == 'step_finish'],
        'tool_result_counts': [r['tool_result_count'] for r in requests if r['advertised_tools']],
        'final_claim_present': FINAL in result.stdout,
        'elapsed_seconds': round(time.monotonic() - started, 2),
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', required=True, type=Path)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not args.node or not args.opencode.is_file():
        parser.error('A Node executable and an existing OpenCode executable are required.')
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='prompt-to-patch-', dir=args.output.resolve()))
    version = subprocess.run([str(args.opencode), '--version'], capture_output=True,
                             text=True, timeout=30).stdout.strip()
    if version != '1.18.30':
        parser.error(f'This reference lab targets OpenCode 1.18.30; found {version}.')
    report = {'release': version, 'os': platform.system(), 'architecture': platform.machine(),
              'provider': 'Local deterministic response fixture; no model inference',
              'cases': [run_case(root, args.opencode.resolve(), args.node, mode)
                        for mode in ['answer_only', 'tool_loop']]}
    report['validation_errors'] = verify_report(report)
    report['passed'] = not report['validation_errors']
    (root / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'run_directory': str(root), **report}, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
