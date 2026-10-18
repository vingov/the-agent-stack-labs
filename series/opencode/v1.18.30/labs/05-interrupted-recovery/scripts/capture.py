"""Private observation primitives. This module does not declare runtime success."""
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request

from contract import sha


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


class Recorder:
    def __init__(self, root, workspace, env, deadline=None):
        self.root, self.workspace, self.env = Path(root), Path(workspace), env
        self.deadline = deadline
        self.lock = threading.RLock()
        self.events = []
        self.trees = {}
        self.url = None
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def timeout(self, requested):
        remaining = requested if self.deadline is None else min(requested, self.deadline - time.monotonic())
        if remaining <= 0:
            raise TimeoutError('Overall collection deadline exceeded')
        return remaining

    def event(self, kind, **details):
        with self.lock:
            item = {'order': len(self.events) + 1, 'time_ns': time.perf_counter_ns(),
                    'utc': datetime.now(timezone.utc).isoformat(), 'kind': kind, **details}
            self.events.append(item)
            write_json(self.root / 'events.json', self.events)
            return item

    def command(self, command, stem, timeout=30, *, cwd=None):
        timeout = self.timeout(timeout)
        start = self.event('command_start', stem=stem)
        timed_out = False
        try:
            result = subprocess.run(command, cwd=cwd or self.workspace, env=self.env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
                                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0)
        except subprocess.TimeoutExpired as error:
            timed_out = True
            result = subprocess.CompletedProcess(command, None, error.stdout or b'', error.stderr or b'')
        end = self.event('command_return', stem=stem, exit=result.returncode, timed_out=timed_out)
        (self.root / (stem + '.stdout')).write_bytes(result.stdout)
        (self.root / (stem + '.stderr')).write_bytes(result.stderr)
        write_json(self.root / (stem + '.process.json'), {
            'command': [str(value) for value in command], 'cwd': str(cwd or self.workspace),
            'start_ns': start['time_ns'], 'end_ns': end['time_ns'], 'timeout_seconds': timeout,
            'returncode': result.returncode, 'timed_out': timed_out,
            'stdout_sha256': sha(result.stdout), 'stderr_sha256': sha(result.stderr)})
        if timed_out:
            raise TimeoutError('Command timed out; diagnostic captures retained: ' + stem)
        return result

    def api(self, method, path, stem, payload=None, timeout=30):
        timeout = self.timeout(timeout)
        if not self.url or not re.fullmatch(r'http://127\.0\.0\.1:\d+', self.url):
            raise ValueError('Expected the owned loopback server origin')
        request_info = {'method': method, 'url': self.url + path, 'payload': payload,
                        'workspace': str(self.workspace), 'timeout_seconds': timeout}
        write_json(self.root / (stem + '.request.json'), request_info)
        start = self.event('api_request', stem=stem)
        status, raw, failure = None, b'', None
        try:
            request = urllib.request.Request(self.url + path, method=method,
                headers={'Content-Type': 'application/json'},
                data=None if payload is None else json.dumps(payload).encode())
            with self.opener.open(request, timeout=timeout) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, raw, failure = error.code, error.read(), str(error)
        except Exception as error:
            failure = repr(error)
        end = self.event('api_return', stem=stem, status=status, failed=failure is not None)
        (self.root / (stem + '.response.json')).write_bytes(raw)
        write_json(self.root / (stem + '.http.json'), {
            'status': status, 'start_ns': start['time_ns'], 'end_ns': end['time_ns'], 'error': failure})
        if failure or status != 200:
            raise RuntimeError('API call failed; captures retained: ' + stem)
        return json.loads(raw)

    def files(self, stem):
        start = self.event('files_start', stem=stem)
        values = {}
        for path in sorted(self.workspace.rglob('*')):
            relative = path.relative_to(self.workspace)
            if '.git' in relative.parts:
                continue
            if path.is_symlink():
                raise RuntimeError('Unexpected symlink in closed fixture')
            if not path.is_file():
                continue
            content = path.read_bytes()
            values[relative.as_posix()] = {'sha256': sha(content), 'bytes': len(content),
                                          'base64': base64.b64encode(content).decode()}
        end = self.event('files_return', stem=stem)
        result = {'start_ns': start['time_ns'], 'end_ns': end['time_ns'], 'files': values}
        write_json(self.root / (stem + '.files.json'), result)
        return result

    def snapshots(self, info, messages, stage):
        refs = {part['snapshot'] for message in messages for part in message['parts'] if part.get('snapshot')}
        refs.update(part['hash'] for message in messages for part in message['parts'] if part['type'] == 'patch')
        if info.get('revert', {}).get('snapshot'):
            refs.add(info['revert']['snapshot'])
        for reference in sorted(refs):
            if reference in self.trees:
                continue
            if not re.fullmatch('[a-f0-9]{40}', reference):
                raise RuntimeError('Unexpected snapshot object identity')
            start = self.event('snapshot_read_start', reference=reference, first_stage=stage)
            candidates = [p.parent for p in (self.root / 'data').rglob('HEAD') if 'snapshot' in p.parts]
            matches = []
            for index, directory in enumerate(candidates):
                result = self.command(['git', '--git-dir=' + str(directory), 'cat-file', '-t', reference],
                                      f'object-{reference}-probe-{index}')
                if result.returncode == 0 and result.stdout.strip() == b'tree':
                    matches.append(directory)
            if len(matches) != 1:
                raise RuntimeError('Snapshot object missing or ambiguous')
            directory, reads = matches[0], 0

            def read(*arguments):
                nonlocal reads
                reads += 1
                value = self.command(['git', '--git-dir=' + str(directory), *arguments],
                                     f'object-{reference}-read-{reads}')
                value.check_returncode()
                return value.stdout

            raw_tree = read('cat-file', 'tree', reference)
            listing = read('ls-tree', '-r', '-z', reference)
            blobs = {}
            for item in listing.split(b'\0'):
                if not item:
                    continue
                metadata, name = item.split(b'\t', 1)
                mode, kind, object_id = metadata.decode().split()
                if kind != 'blob' or b'/' in name or b'\\' in name:
                    raise RuntimeError('Expected a flat regular-file fixture snapshot')
                content = read('cat-file', 'blob', object_id)
                blobs[name.decode()] = {'mode': mode, 'object': object_id,
                                        'base64': base64.b64encode(content).decode()}
            end = self.event('snapshot_read_return', reference=reference, first_stage=stage)
            self.trees[reference] = {'gitdir': str(directory), 'first_stage': stage,
                'start_ns': start['time_ns'], 'end_ns': end['time_ns'],
                'object_base64': base64.b64encode(raw_tree).decode(), 'files': blobs}
            write_json(self.root / 'snapshot-trees.json', self.trees)
        write_json(self.root / (stage + '.snapshot-refs.json'), sorted(refs))
