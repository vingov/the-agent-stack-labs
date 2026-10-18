"""Independent reconstruction of private captures. No OpenCode execution here."""
import base64
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re

from contract import BINARY_SHA256, CALLS, FILES, IMMUTABLE, PIN, PROMPT, TEST_NAMES, fixture, intended_files, sha


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def implementation_inventory(files):
    # These five modules and seven fixtures existed in every admitted collector.
    # Verification and test modules were added later and are not required of pilots.
    essential = {'scripts/' + name + '.py' for name in
                 ('capture', 'contract', 'provider', 'run_lab', 'winprocess')}
    essential.update('fixtures/' + name for name in FILES)
    require(isinstance(files, dict) and essential <= set(files), 'Missing essential collector/fixture provenance')
    for name, digest in files.items():
        require(isinstance(name, str) and re.fullmatch(r'(scripts|fixtures)/[^/\\:]+', name)
                and name.rsplit('/', 1)[1] not in ('.', '..'), 'Unsafe implementation manifest path')
        require(isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest), 'Invalid implementation digest')


def process_history(observations):
    """Check one retained identity; overlapping queries do not establish an order."""
    ended = []
    for item in observations:
        require(type(item['start_ns']) is int and type(item['end_ns']) is int
                and 0 <= item['start_ns'] <= item['end_ns'], 'Invalid process query interval')
        require(type(item['alive']) is bool and
                (item['exit_code'] is None if item['alive'] else type(item['exit_code']) is int),
                'Contradictory process result')
        if not item['alive']:
            ended.append(item)
    if ended:
        first_end = min(item['end_ns'] for item in ended)
        require(len({item['exit_code'] for item in ended}) == 1, 'Retained process exit result changed')
        require(all(not item['alive'] or item['start_ns'] < first_end for item in observations),
                'Exited retained process was later observed alive')


def b64(value):
    try:
        return base64.b64decode(value, validate=True)
    except Exception as error:
        raise EvidenceError('Invalid captured base64') from error


def git_hash(kind, content):
    return hashlib.sha1(kind.encode() + b' ' + str(len(content)).encode() + b'\0' + content).hexdigest()


def tree_files(reference, tree):
    raw = b64(tree['object_base64'])
    require(git_hash('tree', raw) == reference, 'Git tree identity does not match its captured bytes')
    entries, offset = {}, 0
    while offset < len(raw):
        end = raw.find(b'\0', offset)
        require(end >= offset and end + 21 <= len(raw), 'Malformed Git tree object')
        mode, name = raw[offset:end].split(b' ', 1)
        name = name.decode('utf-8')
        require(name in FILES and name not in entries and mode == b'100644', 'Unexpected snapshot entry')
        entries[name] = (mode.decode(), raw[end + 1:end + 21].hex())
        offset = end + 21
    require(set(entries) == set(tree['files']) == set(FILES), 'Snapshot membership differs from the closed fixture')
    result = {}
    for name, (mode, object_id) in entries.items():
        value = tree['files'][name]
        content = b64(value['base64'])
        require(value['mode'] == mode and value['object'] == object_id and git_hash('blob', content) == object_id,
                'Git blob content or membership does not match: ' + name)
        result[name] = content
    return result


def decode_files(record):
    require(record['start_ns'] <= record['end_ns'], 'Invalid file-read interval')
    require(set(record['files']) == set(FILES), 'Unexpected fixture inventory')
    result = {}
    for name, item in record['files'].items():
        content = b64(item['base64'])
        require(sha(content) == item['sha256'] and len(content) == item['bytes'], 'File bytes/hash disagreement: ' + name)
        result[name] = content
    for name in IMMUTABLE:
        require(result[name] == fixture(name), 'Fixed input/helper/test changed: ' + name)
    return result


def acceptance(files):
    original, fixed = fixture('labels.mjs'), intended_files()['labels.mjs']
    require(files['labels.mjs'] in (original, fixed), 'Unknown source behavior outside the prescribed edit')
    trimmed = files['labels.mjs'] == fixed
    catalogue = json.loads(files['catalogue.json'])
    manifest = json.loads(files['catalogue.manifest.json'])
    return [True, trimmed, trimmed, True,
            catalogue == {'labels': ['Alpha', 'Beta  Gamma', 'Delta']},
            manifest == {'algorithm': 'sha256', 'catalogueSha256': sha(files['catalogue.json'])}]


class Reader:
    def __init__(self, root, overrides=None):
        self.root = Path(root)
        self.overrides = overrides or {}

    def bytes(self, name):
        return self.overrides[name] if name in self.overrides else (self.root / name).read_bytes()

    def json(self, name):
        return json.loads(self.bytes(name))

    def text(self, name):
        return self.bytes(name).decode('utf-8')


class Case:
    def __init__(self, reader, name):
        self.reader, self.name = reader, name
        self.identity = self.load('identity.json')
        self.sid = self.identity['session']
        require(self.identity['case'] == name and self.identity['source_commit'] == PIN, 'Case identity mismatch')
        self.workspace = PureWindowsPath(self.identity['workspace'])
        self.profile = self.load('profile-identity.json')
        require(self.profile['nonce'] == self.identity['nonce'] and self.profile['workspace'] == str(self.workspace),
                'Profile/workspace identity mismatch')
        self.events = self.load('events.json')
        require([e['order'] for e in self.events] == list(range(1, len(self.events) + 1)), 'Broken controller event order')
        require(all(a['time_ns'] <= b['time_ns'] for a, b in zip(self.events, self.events[1:])), 'Controller time moved backward')
        require(not any(e['kind'] in ('collection_error', 'provider_error', 'process_monitor_error') for e in self.events),
                'Collection/provider/process-observer failure')
        require(self.load('cleanup.json')['errors'] == [], 'Cleanup did not complete')
        require(self.event('case_capture_complete', case=name), 'Missing complete capture marker')
        self.origins = {stem: self.event('server_ready', stem=stem)['url'] for stem in ('server-1', 'server-2')}
        self.trees = self.load('snapshot-trees.json')
        self.tree_bytes = {reference: tree_files(reference, value) for reference, value in self.trees.items()}
        self.states = {}
        self.parts = {}
        self.infos = {}
        self.raw_files = {}
        self.intervals = {}
        self.ancestry = self.load('barrier-ancestry.json')
        self.identities = self.ancestry['observations']
        require(set(self.identities) == {'generator', 'shell', 'server'}, 'Missing process identity')
        require(self.ancestry['chain'] == [self.identities[k]['pid'] for k in ('generator', 'shell', 'server')],
                'Process chain disagrees with retained identities')
        require(self.identities['server']['creation_time_100ns'] <= self.identities['shell']['creation_time_100ns']
                <= self.identities['generator']['creation_time_100ns'], 'Invalid process creation ordering')
        self.config = json.loads(self.read('resolved-config.stdout'))
        self.node = self.load('node-version.process.json')['command'][0]
        for role, item in self.identities.items():
            self.process(item, role)
            require(item['alive'], 'Barrier process identity was not alive')
        require(self.identities['server']['image_sha256'] == BINARY_SHA256, 'Wrong observed server executable')
        require(PureWindowsPath(self.identities['generator']['image']) == PureWindowsPath(self.node), 'Wrong Node executable')
        require(PureWindowsPath(self.identities['shell']['image']) == PureWindowsPath(self.config['shell']), 'Wrong shell executable')

    def read(self, name):
        return self.reader.bytes(self.name + '/' + name)

    def load(self, name):
        return json.loads(self.read(name))

    def event(self, kind, **fields):
        values = [e for e in self.events if e['kind'] == kind and all(e.get(k) == v for k, v in fields.items())]
        require(len(values) == 1, 'Expected one controller event: ' + kind + ' ' + str(fields))
        return values[0]

    def api(self, stem, path, method='GET', payload=None, second=False):
        request = self.load(stem + '.request.json')
        http = self.load(stem + '.http.json')
        start, end = self.event('api_request', stem=stem), self.event('api_return', stem=stem)
        require(http['start_ns'] == start['time_ns'] <= end['time_ns'] == http['end_ns'], 'API interval mismatch')
        require(http['status'] == 200 and http['error'] is None and end['status'] == 200 and not end['failed'],
                'API operation did not succeed')
        origin = self.origins['server-2' if second else 'server-1']
        require(request['method'] == method and request['url'] == origin + path and request['payload'] == payload,
                'Wrong API method, route, session or payload')
        require(PureWindowsPath(request['workspace']) == self.workspace, 'API directory routing mismatch')
        self.intervals[stem] = [http['start_ns'], http['end_ns']]
        return self.load(stem + '.response.json')

    def command(self, stem):
        value = self.load(stem + '.process.json')
        start, end = self.event('command_start', stem=stem), self.event('command_return', stem=stem)
        require(value['start_ns'] == start['time_ns'] <= end['time_ns'] == value['end_ns'], 'Command interval mismatch')
        require(not value['timed_out'] and not end['timed_out'], 'Timed-out command')
        require(end['exit'] == value['returncode'], 'Command return-code mismatch')
        require(PureWindowsPath(value['cwd']) == self.workspace, 'Wrong command workspace')
        for stream in ('stdout', 'stderr'):
            require(sha(self.read(stem + '.' + stream)) == value[stream + '_sha256'], 'Command output digest mismatch')
        return value

    def process(self, item, role):
        identity = self.identities[role]
        for key in ('pid', 'creation_time_100ns', 'image', 'image_sha256'):
            require(item[key] == identity[key], 'Process identity changed: ' + role)
        require(item['start_ns'] <= item['end_ns'] and item['creation_time_100ns'] > 0, 'Bad process observation interval')
        require(type(item['alive']) is bool and item['wait_result'] == (258 if item['alive'] else 0), 'Failed/contradictory process wait')
        if item['alive']:
            require(item['exit_code'] is None and item['exit_time_100ns'] is None, 'Live process assigned an exit')
        else:
            require(type(item['exit_code']) is int and item['exit_time_100ns'] >= item['creation_time_100ns'],
                    'Missing confirmed process exit')

    def process_group(self, stem):
        group = self.load(stem + '.processes.json')
        start = self.event('process_observation_start', stem=stem)['time_ns']
        end = self.event('process_observation_return', stem=stem)['time_ns']
        require(group['start_ns'] == start <= end == group['end_ns'], 'Process group interval mismatch')
        require(set(group['processes']) == set(self.identities), 'Incomplete owned-process observation')
        for role, item in group['processes'].items():
            self.process(item, role)
            require(start <= item['start_ns'] <= item['end_ns'] <= end, 'Process query outside its capture interval')
        return group

    def state(self, stage, second=False, remote=True):
        metadata = self.load(stage + '.state.json')
        start = self.event('state_start', stage=stage)['time_ns']
        end = self.event('state_return', stage=stage)['time_ns']
        require(metadata['start_ns'] == start <= end == metadata['end_ns'] and metadata['remote'] == remote,
                'Invalid state interval or read surface')
        require(metadata['session'] == self.sid, 'State belongs to another session')
        parts, references, status = [], [], None
        if remote:
            status = self.api(stage + '-status', '/session/status', second=second).get(self.sid)
            info = self.api(stage + '-session', '/session/' + self.sid, second=second)
            messages = self.api(stage + '-messages', '/session/' + self.sid + '/message', second=second)
            require(info['id'] == self.sid and PureWindowsPath(info['directory']) == self.workspace, 'Wrong session readback')
            self.infos[stage] = info
            for message in messages:
                require(message['info']['sessionID'] == self.sid, 'Message ownership mismatch')
                for part in message['parts']:
                    require(part['sessionID'] == self.sid and part['messageID'] == message['info']['id'], 'Tool/part ownership mismatch')
                    parts.append(part)
            refs = {p['snapshot'] for p in parts if p.get('snapshot')}
            refs.update(p['hash'] for p in parts if p['type'] == 'patch')
            if info.get('revert', {}).get('snapshot'):
                refs.add(info['revert']['snapshot'])
            references = self.load(stage + '.snapshot-refs.json')
            require(references == sorted(refs), 'Snapshot references disagree with actual parts')
            require(set(references) <= set(self.trees), 'Snapshot bytes are unavailable')
            self.parts[stage] = parts
            require(start <= self.intervals[stage + '-messages'][0] <= self.intervals[stage + '-messages'][1] <= end,
                    'Message read outside the state observation')
        before = self.load(stage + '-before-test.files.json')
        after = self.load(stage + '-after-test.files.json')
        files, after_files = decode_files(before), decode_files(after)
        require(files == after_files, 'Acceptance check changed the captured files')
        for suffix, record in (('before-test', before), ('after-test', after)):
            stem = stage + '-' + suffix
            require(record['start_ns'] == self.event('files_start', stem=stem)['time_ns']
                    and record['end_ns'] == self.event('files_return', stem=stem)['time_ns'], 'File capture interval mismatch')
        command = self.command(stage + '-acceptance')
        require(command['command'] == [self.node, '--test', '--test-reporter=tap', 'acceptance.test.mjs'], 'Wrong acceptance command')
        require(start <= before['start_ns'] <= before['end_ns'] <= command['start_ns'] <= command['end_ns']
                <= after['start_ns'] <= after['end_ns'] <= end, 'Tests are not bracketed by the captured files')
        if remote:
            require(self.intervals[stage + '-messages'][1] <= before['start_ns'], 'File witness precedes required message read')
        tap = self.read(stage + '-acceptance.stdout').decode('utf-8')
        tests = re.findall(r'^(not )?ok (\d+) - (.+)$', tap, re.M)
        require([name for _, _, name in tests] == list(TEST_NAMES), 'Named test inventory changed')
        require([int(index) for _, index, _ in tests] == list(range(1, 7)), 'Duplicate/missing test result')
        results = [not bool(failed) for failed, _, _ in tests]
        require(results == acceptance(files), 'Test outcomes contradict independently inspected artifacts')
        require(command['returncode'] == (0 if all(results) else 1), 'Test exit contradicts named outcomes')
        require(re.search(r'^# pass ' + str(sum(results)) + '$', tap, re.M)
                and re.search(r'^# fail ' + str(6 - sum(results)) + '$', tap, re.M), 'TAP totals disagree with named tests')
        self.raw_files[stage] = files
        summary = {'interval': [start, end], 'file_witness_interval': [before['start_ns'], before['end_ns']],
            'remote_read_available': remote, 'session_status_entry': status,
            'files': {name: {'sha256': sha(content), 'bytes': len(content)} for name, content in files.items()},
            'tests': dict(zip(TEST_NAMES, results)), 'snapshot_refs': references,
            'patches': [{'hash': p['hash'], 'files': [self.relative(name) for name in p['files']]}
                        for p in parts if p['type'] == 'patch'],
            'tools': [{'call_id': p['callID'], 'part_id': p['id'], 'tool': p['tool'],
                       'status': p['state']['status'], 'input': p['state'].get('input'),
                       'exit': p['state'].get('metadata', {}).get('exit'),
                       'interrupted': p['state'].get('metadata', {}).get('interrupted', False),
                       'abort_error': p['state'].get('error') == 'Tool execution aborted',
                       'cancellation_output': 'User aborted the command' in p['state'].get('output', '')}
                      for p in parts if p['type'] == 'tool'],
            'provider_requests': metadata['provider_requests']}
        self.states[stage] = summary
        return summary

    def relative(self, path):
        try:
            name = PureWindowsPath(path).relative_to(self.workspace).as_posix()
        except ValueError as error:
            raise EvidenceError('Patch path escapes its workspace') from error
        require(name in FILES, 'Patch selects an unexpected fixture path')
        return name

    def validate(self):
        from contract import COMMAND, roles
        for stem in ('version', 'node-version', 'shell-version', 'git-version', 'resolved-config', 'resolved-agent'):
            require(self.command(stem)['returncode'] == 0, 'Toolchain inspection failed')
        require(self.read('version.stdout').strip() == b'1.18.30', 'Wrong CLI release')
        config, env = self.load('opencode.json'), self.load('environment.json')
        for key, value in config.items():
            if key != 'agent':
                require(self.config[key] == value, 'Resolved configuration drift: ' + key)
        require(config['agent'] == roles() and config['snapshot'] is True and config['enabled_providers'] == ['lab'],
                'Unexpected agent/provider/snapshot configuration')
        require(re.fullmatch(r'http://127\.0\.0\.1:\d+/v1', config['provider']['lab']['options']['baseURL']),
                'Provider is not loopback-only')
        require(env['LAB_RUN_NONCE'] == self.identity['nonce'] and env['OPENCODE_EXPERIMENTAL_NATIVE_LLM'] == 'false'
                and env['OPENCODE_EXPERIMENTAL'] == 'false', 'Wrong task identity or runtime path')
        for key, profile_key in (('XDG_DATA_HOME', 'data'), ('OPENCODE_CONFIG', 'config')):
            require(env[key] == self.profile[profile_key], 'Different persistence profile')
        launch1, launch2, client = [self.load(stem + '.launch.json') for stem in ('server-1', 'server-2', 'client')]
        for launch in (launch1, launch2, client):
            for key, filename in (('profile_sha256', 'profile-identity.json'), ('config_sha256', 'opencode.json'),
                                  ('environment_sha256', 'environment.json')):
                require(launch[key] == sha(self.read(filename)), 'Launch profile/config/environment drift')
            require(PureWindowsPath(launch['cwd']) == self.workspace, 'Wrong launch workspace')
            require(launch['identity']['image_sha256'] == BINARY_SHA256, 'Wrong launched binary')
        require(launch1['command'] == launch2['command'], 'Restart command drift')
        require(launch1['identity']['creation_time_100ns'] < launch2['identity']['creation_time_100ns'],
                'Restart did not create a new server process')
        require(client['command'][1:] == ['run', '--pure', '--attach', self.origins['server-1'], '--session', self.sid,
                '--format', 'json', '--model', 'lab/scripted', '--agent', 'builder', '--', PROMPT], 'Wrong task invocation')
        self.api('create-session', '/session', 'POST', {'title': 'Synthetic interrupted catalogue',
                 'agent': 'builder', 'model': {'providerID': 'lab', 'id': 'scripted'}})
        stages = ['initial', 'barrier', 'primary'] + ([] if self.name == 'forced' else ['reopened'])
        stages += ['restarted', 'reverted', 'unreverted']
        for stage in stages:
            self.state(stage, second=stage in ('restarted', 'reverted', 'unreverted'),
                       remote=not (stage == 'primary' and self.name == 'forced'))
        require(all(self.states[a]['interval'][1] <= self.states[b]['interval'][0]
                    for a, b in zip(stages, stages[1:])), 'State observations out of order')
        original = {name: fixture(name) for name in FILES}
        partial = intended_files()
        partial['catalogue.manifest.json'] = original['catalogue.manifest.json']
        require(self.raw_files['initial'] == original and self.raw_files['barrier'] == partial,
                'Initial or independently witnessed barrier bytes changed')
        admission = self.load('barrier-admission.json')
        target = admission['user_message']
        users = [m for m in self.load('barrier-messages.response.json') if m['info']['role'] == 'user']
        require(len(users) == 1 and users[0]['info']['id'] == target, 'Wrong recovery boundary')
        # The Windows CLI can persist the argument's surrounding literal quotes.
        require(any(p['type'] == 'text' and p['text'] in (PROMPT, json.dumps(PROMPT)) for p in users[0]['parts']),
                'Task text mismatch')
        tools = self.states['barrier']['tools']
        require([(p['call_id'], p['tool'], p['input']) for p in tools] == CALLS, 'Tool history differs from prescribed calls')
        require([p['status'] for p in tools] == ['completed'] * 5 + ['running'], 'Barrier is not an unfinished tool')
        require(admission['tool_call'] == tools[-1]['call_id'] and admission['tool_part'] == tools[-1]['part_id']
                and admission['release_present'] is False, 'Barrier admission identity mismatch')
        self.process(admission['process'], 'generator')
        require(admission['process']['alive'], 'Generator was not alive at admission')
        admitted = self.event('barrier_admitted', target=target, tool_part=tools[-1]['part_id'])
        require(self.states['barrier']['interval'][1] <= admission['process']['start_ns']
                <= admission['process']['end_ns'] <= admitted['time_ns'], 'Admission precedes the barrier evidence')
        for reference, tree in self.trees.items():
            stage = tree['first_stage']
            start = self.event('snapshot_read_start', reference=reference, first_stage=stage)['time_ns']
            end = self.event('snapshot_read_return', reference=reference, first_stage=stage)['time_ns']
            require(tree['start_ns'] == start <= end == tree['end_ns'], 'Snapshot observation interval mismatch')
            require(reference in self.states[stage]['snapshot_refs'] and self.states[stage]['interval'][0] <= start
                    <= end <= self.states[stage]['interval'][1], 'Retrospective or unrelated snapshot evidence')
            prefix = 'object-' + reference + '-read-'
            command = self.command(prefix + '1')
            require(command['command'] == ['git', '--git-dir=' + tree['gitdir'], 'cat-file', 'tree', reference]
                    and self.read(prefix + '1.stdout') == b64(tree['object_base64']), 'Tree is not the captured Git object')
            listing = self.read(prefix + '2.stdout').split(b'\0')
            expected_listing = [value['mode'].encode() + b' blob ' + value['object'].encode() + b'\t' + name.encode()
                                for name, value in sorted(tree['files'].items())]
            require([item for item in listing if item] == expected_listing, 'Git listing disagrees with tree')
            for index, name in enumerate(sorted(tree['files']), 3):
                value = self.command(prefix + str(index))
                require(value['command'] == ['git', '--git-dir=' + tree['gitdir'], 'cat-file', 'blob', tree['files'][name]['object']]
                        and self.read(prefix + str(index) + '.stdout') == self.tree_bytes[reference][name]
                        and start <= value['start_ns'] <= value['end_ns'] <= end, 'Blob capture provenance mismatch')
        old_refs = [ref for ref in self.states['barrier']['snapshot_refs']
                    if self.trees[ref]['end_ns'] <= admitted['time_ns'] and self.tree_bytes[ref]['catalogue.json'] == original['catalogue.json']]
        require(old_refs, 'No actual pre-intervention saved catalogue bytes')
        if self.name == 'graceful':
            require(self.api('abort', '/session/' + self.sid + '/abort', 'POST', {}) is True, 'Abort response mismatch')
            intervention = self.intervals['abort']
        elif self.name == 'normal':
            intervention = [self.event('control_marker_start', name='release.json')['time_ns'],
                            self.event('control_marker_return', name='release.json')['time_ns']]
        else:
            intervention = [self.event('harness_process_termination_start', stem='server-1', cause='active-server-stop')['time_ns'],
                            self.event('harness_process_termination_return', stem='server-1', cause='active-server-stop')['time_ns']]
            termination = self.load('server-1-active-server-stop.termination.json')
            self.process(termination['before'], 'server')
            self.process(termination['after'], 'server')
            require(termination['requested'] and not termination['after']['alive'], 'Forced stop not confirmed')
            require('catalogue.json' not in {name for patch in self.states['barrier']['patches'] for name in patch['files']},
                    'Forced-stop comparison lacks the coverage gap at intervention')
        require(admitted['time_ns'] <= intervention[0] <= intervention[1] <= self.states['primary']['interval'][0],
                'Intervention ordering is invalid')
        immediate = self.process_group('immediate-post-intervention')
        require(intervention[1] <= immediate['start_ns'] <= immediate['end_ns'] <= self.states['primary']['interval'][0],
                'Immediate process observation is not after the intervention')
        files = self.load('immediate-post-intervention.files.json')
        decode_files(files)
        require(intervention[1] <= files['start_ns'] <= files['end_ns'] <= self.states['primary']['interval'][0],
                'Immediate file observation is out of order')
        samples = [json.loads(line) for line in self.read('process-samples.jsonl').splitlines()]
        require(len(samples) >= 2, 'Process monitor evidence missing')
        for role in self.identities:
            previous = None
            for sample in samples:
                require(set(sample) == set(self.identities), 'Incomplete process sample')
                item = sample[role]
                self.process(item, role)
                if previous:
                    require(previous['end_ns'] <= item['start_ns'] and (previous['alive'] or not item['alive']),
                            'Process samples contradict retained-handle lifecycle')
                previous = item
        primary_end = self.states['primary']['interval'][1]
        cleanup_actions = [e for e in self.events if e['kind'] in ('harness_child_termination_start', 'emergency_child_cleanup')
                           or (e['kind'] == 'control_marker_start' and e['name'] == 'stop.json')]
        require(cleanup_actions and all(e['time_ns'] >= primary_end for e in cleanup_actions),
                'Harness cleanup contaminated the primary observation')
        cleanup_start = min(e['time_ns'] for e in cleanup_actions)
        first_exit = next((s['generator'] for s in samples if not s['generator']['alive']), None)
        cleanup_stem = 'forced' if self.name == 'forced' else 'primary'
        before_cleanup = self.process_group(cleanup_stem + '-before-cleanup')
        after_cleanup = self.process_group(cleanup_stem + '-after-cleanup')
        require(primary_end <= before_cleanup['start_ns'] <= after_cleanup['start_ns']
                and all(not after_cleanup['processes'][role]['alive'] for role in ('shell', 'generator')),
                'Children not confirmed absent before restart')
        require(before_cleanup['end_ns'] <= after_cleanup['start_ns'], 'Cleanup observation groups overlap')
        require(after_cleanup['end_ns'] <= self.event('restart_begin')['time_ns'], 'Cleanup completed after restart began')
        require(primary_end <= samples[-1]['generator']['end_ns'] <= before_cleanup['start_ns'],
                'Process monitor does not cover primary through the cleanup boundary')
        for role in self.identities:
            observations = [self.identities[role], immediate['processes'][role],
                            before_cleanup['processes'][role], after_cleanup['processes'][role]]
            observations.extend(sample[role] for sample in samples)
            if role == 'generator':
                observations.append(admission['process'])
            if role == 'server' and self.name == 'forced':
                observations.extend((termination['before'], termination['after']))
            process_history(observations)
            require(len({item['exit_time_100ns'] for item in observations if not item['alive']}) <= 1,
                    'Retained process exit time changed')
        process_summary = {'immediate': {role: {'alive': p['alive'], 'exit_code': p['exit_code'],
            'query_interval': [p['start_ns'], p['end_ns']]} for role, p in immediate['processes'].items()},
            'generator_exit_observed_before_harness_cleanup': bool(first_exit and first_exit['end_ns'] < cleanup_start),
            'first_generator_exit_query_interval': None if first_exit is None else [first_exit['start_ns'], first_exit['end_ns']],
            'cleanup_start_ns': cleanup_start, 'sample_count': len(samples),
            'monitor_interval': [samples[0]['generator']['start_ns'], samples[-1]['generator']['end_ns']],
            'last_monitored_generator': {key: samples[-1]['generator'][key] for key in ('start_ns', 'end_ns', 'alive', 'exit_code')},
            'before_cleanup': {role: {'alive': p['alive'], 'exit_code': p['exit_code'],
                                     'query_interval': [p['start_ns'], p['end_ns']]}
                               for role, p in before_cleanup['processes'].items()},
            'after_cleanup': {role: {'alive': p['alive'], 'exit_code': p['exit_code'],
                                    'query_interval': [p['start_ns'], p['end_ns']]}
                              for role, p in after_cleanup['processes'].items()},
            'identities': {role: {key: p[key] for key in ('pid', 'creation_time_100ns', 'image_sha256')}
                           | {'image_basename': PureWindowsPath(p['image']).name} for role, p in self.identities.items()}}
        quiescent = decode_files(self.load('quiescent-before-restart.files.json'))
        require(quiescent == self.raw_files['restarted'], 'Restart changed the independently observed files')
        previous = 'barrier' if self.name == 'forced' else 'reopened'
        require(self.parts[previous] == self.parts['restarted'], 'Durable parts changed across restart')
        if self.name != 'forced':
            require(self.parts['primary'] == self.parts['reopened'] and self.raw_files['primary'] == quiescent,
                    'Primary evidence changed before restart')
        require(not self.infos['restarted'].get('revert'), 'This is not the first revert')
        self.api('first-revert', '/session/' + self.sid + '/revert', 'POST', {'messageID': target}, second=True)
        self.api('unrevert', '/session/' + self.sid + '/unrevert', 'POST', {}, second=True)
        require(self.states['restarted']['interval'][1] <= self.intervals['first-revert'][0]
                <= self.intervals['first-revert'][1] <= self.states['reverted']['interval'][0]
                <= self.states['reverted']['interval'][1] <= self.intervals['unrevert'][0]
                <= self.intervals['unrevert'][1] <= self.states['unreverted']['interval'][0], 'Recovery observation ordering mismatch')
        selection = {}
        for patch in self.states['restarted']['patches']:
            for name in patch['files']:
                selection.setdefault(name, patch['hash'])
        predicted = dict(self.raw_files['restarted'])
        for name, reference in selection.items():
            predicted[name] = self.tree_bytes[reference][name]
        preundo = self.infos['reverted']['revert']['snapshot']
        require(self.infos['reverted']['revert']['messageID'] == target, 'Revert marker boundary differs')
        require(self.tree_bytes[preundo] == self.raw_files['restarted'], 'Unrevert snapshot differs from actual pre-undo files')
        require(self.raw_files['reverted'] == predicted, 'First revert bytes disagree with recorded path selection')
        require(self.raw_files['unreverted'] == self.tree_bytes[preundo] and not self.infos['unreverted'].get('revert'),
                'Unrevert did not restore the pre-undo bytes and clear the marker')
        provider_events = [e for e in self.events if e['kind'] == 'provider_request']
        require([e['request'] for e in provider_events] == list(range(1, len(provider_events) + 1)), 'Provider inventory incomplete')
        main_calls = []
        for event in provider_events:
            index = event['request']
            request, response = self.load(f'provider-{index:02}.request.json'), self.load(f'provider-{index:02}.response.json')
            require(request['path'] == '/v1/chat/completions', 'Wrong provider route')
            if response['kind'] != 'main':
                continue
            require(request['headers']['x-session-id'] == self.sid, 'Provider session mismatch')
            replies = [m['tool_call_id'] for m in request['body']['messages'] if m['role'] == 'tool']
            require(replies == [c[0] for c in CALLS[:len(replies)]], 'Provider tool history mismatch')
            calls = response['message'].get('tool_calls', [])
            if calls:
                require(len(calls) == 1 and len(replies) < len(CALLS), 'Unexpected provider tool selection')
                call = calls[0]
                actual = (call['id'], call['function']['name'], json.loads(call['function']['arguments']))
                require(actual == CALLS[len(replies)], 'Provider choices differ from prescribed task')
                main_calls.append(actual)
        require(main_calls == CALLS, 'Prescribed sequence missing or repeated')
        require(all(e['time_ns'] < self.states['primary']['interval'][1] for e in provider_events),
                'Unplanned provider continuation during recovery')
        require(all(self.states[s]['provider_requests'] == len(provider_events) for s in stages[2:]),
                'Provider request counts contradict the captured inventory')
        changed = sorted(name for name in FILES if quiescent[name] != original[name])
        return {'case': self.name, 'session': self.sid, 'user_message': target,
            'states': self.states, 'intervention_interval': intervention, 'process': process_summary,
            'pre_intervention_saved_catalogue_refs': old_refs, 'selected_earliest_refs': selection,
            'changed_paths_before_revert': changed, 'unselected_changed_paths': sorted(set(changed) - set(selection)),
            'preundo_snapshot': preundo, 'restored_baseline': self.raw_files['reverted'] == original,
            'unrevert_restored_preundo': True, 'provider_request_count': len(provider_events),
            'trees': {ref: {key: value for key, value in tree.items() if key != 'gitdir'} for ref, tree in self.trees.items()}}


def verify(root, implementation=None, overrides=None):
    reader = Reader(root, overrides)
    metadata = reader.json('run.json')
    require(metadata['source_commit'] == PIN and metadata['binary_sha256'] == BINARY_SHA256, 'Run pin mismatch')
    require(metadata['cases'] in (['normal', 'graceful'], ['normal', 'graceful', 'forced']), 'Unexpected case inventory')
    source = Path(implementation) if implementation else Path(root) / 'implementation'
    implementation_inventory(metadata['files'])
    archived = {path.relative_to(source).as_posix() for folder in ('scripts', 'fixtures')
                for path in (source / folder).rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    require(set(metadata['files']) == archived, 'Implementation manifest membership differs from archive')
    for name, digest in metadata['files'].items():
        require(sha((source / name).read_bytes()) == digest, 'Executed implementation identity mismatch: ' + name)
    for name in FILES:
        require((source / 'fixtures' / name).read_bytes() == fixture(name), 'Verifier fixture differs from executed fixture')
    cases = [Case(reader, name).validate() for name in metadata['cases']]
    require(len({case['session'] for case in cases}) == len(cases), 'Cases share a session identity')
    return {'schema': 1, 'evidence_class': 'Windows CLI; scripted loopback provider; no model inference',
            'run_id': metadata['run_id'], 'created_utc': metadata['created_utc'], 'platform': metadata['platform'],
            'source_commit': PIN, 'binary_sha256': BINARY_SHA256, 'implementation_sha256': metadata['files'],
            'verification_scope': 'Consistency of captured observations; not independent authentication of historical execution',
            'cases': cases}
