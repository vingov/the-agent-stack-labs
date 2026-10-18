"""Loopback-only prescribed tool choices; no model inference or credentials."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from capture import write_json
from contract import CALLS, FINAL


class ScriptedProvider:
    def __init__(self, recorder):
        self.recorder, self.count, self.session = recorder, 0, None
        self.errors = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(15)

            def log_message(self, *args):
                pass

            def do_POST(self):
                try:
                    length = int(self.headers['Content-Length'])
                    if not 0 < length <= 16 * 1024 * 1024:
                        raise ValueError('Unexpected provider request length')
                    body = json.loads(self.rfile.read(length))
                    with recorder.lock:
                        owner.count += 1
                        index = owner.count
                    if index > 16 or self.path != '/v1/chat/completions':
                        raise ValueError('Unexpected provider route or request count')
                    headers = {key.lower(): value for key, value in self.headers.items()
                               if key.lower() in ('x-session-id', 'x-session-affinity', 'x-parent-session-id')}
                    write_json(recorder.root / f'provider-{index:02}.request.json', {
                        'path': self.path, 'headers': headers, 'body': body})
                    recorder.event('provider_request', request=index)
                    available = {tool['function']['name'] for tool in body.get('tools', [])}
                    replies = [message for message in body.get('messages', []) if message['role'] == 'tool']
                    main, call = bool(available), None
                    if main:
                        if headers.get('x-session-id') != owner.session:
                            raise ValueError('Provider request belongs to another session')
                        if len(replies) > len(CALLS) or [r['tool_call_id'] for r in replies] != [c[0] for c in CALLS[:len(replies)]]:
                            raise ValueError('Unexpected prescribed tool history')
                        call = CALLS[len(replies)] if len(replies) < len(CALLS) else None
                    message = {'role': 'assistant', 'content': FINAL if main else 'Synthetic catalogue task'}
                    reason = 'stop'
                    if call:
                        ident, name, args = call
                        if name not in available:
                            raise ValueError('Required tool was not exposed')
                        message = {'role': 'assistant', 'tool_calls': [{
                            'index': 0, 'id': ident, 'type': 'function',
                            'function': {'name': name, 'arguments': json.dumps(args)}}]}
                        reason = 'tool_calls'
                    write_json(recorder.root / f'provider-{index:02}.response.json', {
                        'kind': 'main' if main else 'auxiliary', 'message': message, 'finish_reason': reason})
                    recorder.event('provider_response', request=index, finish=reason)
                    usage = {'prompt_tokens': 20, 'completion_tokens': 2, 'total_tokens': 22}
                    self.send_response(200)
                    if not body.get('stream'):
                        raw = json.dumps({'id': 'lab', 'object': 'chat.completion', 'model': 'scripted',
                            'choices': [{'index': 0, 'message': message, 'finish_reason': reason}], 'usage': usage}).encode()
                        self.send_header('Content-Type', 'application/json')
                        self.send_header('Content-Length', str(len(raw)))
                        self.end_headers()
                        self.wfile.write(raw)
                        return
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Connection', 'close')
                    self.end_headers()
                    for delta, finish in ((message, None), ({}, reason)):
                        chunk = {'id': 'lab', 'object': 'chat.completion.chunk', 'model': 'scripted',
                                 'choices': [{'index': 0, 'delta': delta, 'finish_reason': finish}]}
                        if finish:
                            chunk['usage'] = usage
                        self.wfile.write(('data: ' + json.dumps(chunk) + '\n\n').encode())
                    self.wfile.write(b'data: [DONE]\n\n')
                    self.wfile.flush()
                except Exception as error:
                    owner.errors.append(repr(error))
                    write_json(recorder.root / 'provider-errors.json', owner.errors)
                    recorder.event('provider_error', error=repr(error))
                    try:
                        self.send_error(500, 'Synthetic provider failed')
                    except OSError:
                        pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .1}, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.server.server_port}/v1'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            raise RuntimeError('Provider thread did not settle')
