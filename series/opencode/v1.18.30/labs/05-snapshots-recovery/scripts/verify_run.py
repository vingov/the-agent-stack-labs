"""Reconstruct a sanitized receipt from raw captures; do not trust success flags."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
from contract import (BINARY_SHA256, CALLS, CASES, CONTINUATION, FILES, FINAL, PIN,
                      PROMPT, STAGES, expected, fixture, roles, sha)

def need(condition, message):
    if not condition:
        raise ValueError(message)

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def path_key(value):
    return value.replace('\\', '/').rstrip('/').casefold()

def object_id(kind, data):
    return hashlib.sha1(kind.encode() + b' ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def tree_contents(trees, key, workspace):
    tree = trees[key]
    need(path_key(tree['gitdir']).startswith(path_key(workspace.rsplit('/', 1)[0]) + '/data/opencode/snapshot/'),
         'snapshot repository outside isolated data')
    raw = base64.b64decode(tree['object_base64'], validate=True)
    need(object_id('tree', raw) == key, 'tree object hash mismatch')
    need(set(tree['files']) == set(FILES), 'unexpected snapshot coverage')
    rebuilt, result = b'', {}
    for name, blob in sorted(tree['files'].items()):
        data = base64.b64decode(blob['base64'], validate=True)
        need(blob['mode'] == '100644', 'unexpected fixture file mode')
        need(object_id('blob', data) == blob['object'], 'blob object hash mismatch')
        rebuilt += blob['mode'].encode() + b' ' + name.encode() + b'\0' + bytes.fromhex(blob['object'])
        result[name] = data
    need(rebuilt == raw, 'tree membership does not match blobs')
    return result

def check_stage(root, case, stage):
    want = expected(case, stage)
    folder = root / stage
    manifest = read(folder / 'manifest.json')
    actual_files = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    need(actual_files == set(FILES) == set(manifest), stage + ': file inventory differs')
    for name, data in want.items():
        actual = (folder / name).read_bytes()
        need(actual == data, stage + ': unexpected bytes in ' + name)
        need(manifest[name] == {'sha256': sha(actual), 'bytes': len(actual)}, stage + ': manifest mismatch')
    passed = stage in ('r1', 'r2', 'r4')
    proc = read(root / (stage + '-test.process.json'))
    need(proc['command'][1:] == ['--test', 'labels.test.mjs'], stage + ': wrong test command')
    need(proc['exit'] == (0 if passed else 1), stage + ': wrong test exit')
    output = (root / (stage + '-test.stdout.txt')).read_text(encoding='utf-8')
    counts = {}
    for key in ('tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo'):
        hits = re.findall(r'^(?:ℹ|#) ' + key + r' (\d+)\s*$', output, re.M)
        need(len(hits) == 1, stage + ': missing or duplicated test count')
        counts[key] = int(hits[0])
    need(counts == {'tests': 4, 'pass': 4 if passed else 2, 'fail': 0 if passed else 2,
                    'cancelled': 0, 'skipped': 0, 'todo': 0}, stage + ': test counts differ')
    value_process = read(root / (stage + '-value.process.json'))
    need(value_process['exit'] == 0 and value_process['command'][1:] == ['--input-type=module', '-e',
         "import {displayMode} from './labels.mjs'; console.log(JSON.stringify({displayMode}));"], 'wrong setting check')
    value = read(root / (stage + '-value.stdout.txt'))
    setting = 'expanded' if case == 'same-file' and stage in ('r2', 'r4') else 'compact'
    need(value == {'displayMode': setting}, stage + ': independent value differs')
    return {'files': manifest, 'tests': counts, 'display_mode': setting}

def reconstruct_case(root, case, include_continuation=False):
    need(not (root / 'provider-errors.json').exists(), 'provider errors recorded')
    identity = read(root / 'identity.json')
    sid, workspace = identity['session'], identity['workspace'].replace('\\', '/')
    need(workspace.endswith('/' + case + '/workspace'), 'unexpected workspace identity')
    need((root / 'version.stdout.txt').read_text().strip() == '1.18.30', 'binary version differs')
    need(path_key((root / 'git-setup-3.stdout.txt').read_text().strip()) == path_key(workspace), 'Git root differs')
    need(not (root / 'git-setup-4.stdout.txt').read_text().strip(), 'fixture was not clean and committed')
    for stem in ['git-setup-' + str(i) for i in range(5)] + ['version', 'node-version', 'git-version', 'resolved-config', 'resolved-agent', 'cli']:
        need(read(root / (stem + '.process.json'))['exit'] == 0, stem + ' failed')
    config = read(root / 'resolved-config.stdout.txt')
    submitted = read(root / 'opencode.json')
    for role in config['agent'].values():
        need(role.pop('options', {}) == {}, 'unexpected agent options')
    for key in ('model', 'small_model', 'default_agent', 'enabled_providers', 'share', 'snapshot', 'lsp', 'formatter', 'permission', 'agent'):
        need(config.get(key) == submitted.get(key), 'resolved configuration differs: ' + key)
    need(config['agent'] == roles() and config['permission'] == {'*': 'deny'}, 'configured rules changed')
    need(config['snapshot'] is True and config['lsp'] is False and config['formatter'] is False, 'fixture services changed')
    need(config['model'] == config['small_model'] == 'lab/scripted' and config['default_agent'] == 'builder', 'model/agent changed')
    need(config['enabled_providers'] == ['lab'] and config['share'] == 'disabled', 'provider/share changed')
    provider = config['provider']['lab']
    need(provider['npm'] == '@ai-sdk/openai-compatible' and provider['options']['apiKey'] == 'lab', 'provider changed')
    need(re.fullmatch(r'http://127\.0\.0\.1:\d+/v1', provider['options']['baseURL']) is not None, 'provider not loopback')
    need(not config.get('experimental'), 'unexpected experimental configuration')
    keys = read(root / 'environment-keys.json')
    need(not any(k.startswith('OPENCODE_EXPERIMENTAL') for k in keys), 'experimental environment')
    need({'HOME', 'USERPROFILE', 'OPENCODE_TEST_HOME', 'XDG_DATA_HOME', 'OPENCODE_CONFIG'} <= set(keys), 'missing state isolation')
    agent = read(root / 'resolved-agent.stdout.txt')
    need(agent['name'] == 'builder' and agent['mode'] == 'primary', 'resolved agent changed')
    for permission, patterns in roles()['builder']['permission'].items():
        for pattern, action in patterns.items():
            matches = [r for r in agent['permission'] if r['permission'] == permission and r['pattern'] == pattern]
            need(matches and matches[-1]['action'] == action, 'resolved permission differs')
    sequence = read(root / 'sequence.json')
    need([e['order'] for e in sequence] == list(range(1, len(sequence) + 1)), 'event order gap')
    def event(kind, **fields):
        rows = [e for e in sequence if e['kind'] == kind and all(e.get(k) == v for k, v in fields.items())]
        need(len(rows) == 1, 'missing or duplicate event: ' + kind + str(fields))
        return rows[0]
    def api(stem, method, suffix, payload):
        req = read(root / (stem + '.request.json'))
        need(req['method'] == method and re.fullmatch(r'http://127\.0\.0\.1:\d+' + re.escape(suffix), req['url']) is not None,
             'wrong API route: ' + stem)
        need(req['payload'] == payload, 'wrong API payload: ' + stem)
        need(read(root / (stem + '.http.json'))['status'] == 200, 'API failure: ' + stem)
        need(event('api_request', stem=stem)['order'] < event('api_return', stem=stem)['order'], 'API return before request')
        return read(root / (stem + '.response.json'))
    created = api('session-create', 'POST', '/session', {'title': 'Synthetic recovery ' + case,
        'agent': 'builder', 'model': {'providerID': 'lab', 'id': 'scripted'}})
    need(created['id'] == sid, 'created session differs')
    origin = read(root / 'session-create.request.json')['url'].removesuffix('/session')
    server = read(root / 'server-command.json')
    need(server[1:] == ['--print-logs', '--log-level', 'INFO', 'serve', '--pure', '--hostname', '127.0.0.1', '--port', '0'], 'server entry differs')
    cli = read(root / 'cli.process.json')['command']
    need(cli[0] == server[0] and cli[1:] == ['run', '--pure', '--attach', origin, '--session', sid,
         '--format', 'json', '--model', 'lab/scripted', '--agent', 'builder', '--', PROMPT], 'attached CLI entry differs')
    for path in root.glob('*.request.json'):
        need(read(path)['url'].startswith(origin + '/'), 'API request reached another server')
    log = (root / 'server.stderr.txt').read_text(encoding='utf-8')
    need('level=ERROR' not in log and 'message="failed' not in log, 'runtime error requires investigation')
    stages = list(STAGES) + (['c0', 'c1'] if include_continuation else [])
    infos, histories, checkpoints, stage_results = {}, {}, {}, {}
    for stage in stages:
        status = api(stage + '-status', 'GET', '/session/status', None)
        need(sid not in status or status[sid]['type'] == 'idle', 'session was busy')
        info = api(stage + '-session', 'GET', '/session/' + sid, None)
        messages = api(stage + '-messages', 'GET', '/session/' + sid + '/message', None)
        api(stage + '-diff', 'GET', '/session/' + sid + '/diff', None)
        need(info['id'] == sid and info['version'] == '1.18.30' and path_key(info['directory']) == path_key(workspace), 'session provenance differs')
        need(info['agent'] == 'builder' and info['model'] == {'id': 'scripted', 'providerID': 'lab'} and not info.get('parentID'), 'session role differs')
        for message in messages:
            mi = message['info']
            need(mi['sessionID'] == sid, 'message owner differs')
            need(all(p['sessionID'] == sid and p['messageID'] == mi['id'] for p in message['parts']), 'part owner differs')
            if mi['role'] == 'assistant':
                need(not mi.get('error') and mi['time'].get('completed'), 'assistant did not complete')
                need(mi['agent'] == 'builder' and mi['providerID'] == 'lab' and mi['modelID'] == 'scripted', 'assistant runtime differs')
                need(path_key(mi['path']['cwd']) == path_key(mi['path']['root']) == path_key(workspace), 'assistant path differs')
        infos[stage], histories[stage] = info, messages
        checkpoints[stage] = event('checkpoint', stage=stage)
        stage_results[stage] = check_stage(root, case, stage)
    need(histories['r0'] == [], 'initial history was not empty')
    initial = histories['r1']
    users = [m for m in initial if m['info']['role'] == 'user']
    need(len(users) == 1, 'unexpected original users')
    target = users[0]['info']['id']
    need([p['text'] for p in users[0]['parts']] in ([PROMPT], [json.dumps(PROMPT)]), 'original prompt differs')
    need(initial[-1]['info']['finish'] == 'stop' and [p['text'] for p in initial[-1]['parts'] if p['type'] == 'text'] == [FINAL], 'final response differs')
    for stage in ('r2', 'r3', 'r4') + (('c0',) if include_continuation else ()):
        need(histories[stage] == initial, 'stored coding records changed before cleanup')
    parts = [p for m in initial for p in m['parts']]
    calls = [p for p in parts if p['type'] == 'tool']
    need([(p['callID'], p['tool'], p['state']['input']) for p in calls] == CALLS, 'tool sequence differs')
    by_call = {p['callID']: p for p in calls}
    for part in calls:
        state = part['state']
        need(state['status'] == 'completed' and state['time']['end'] >= state['time']['start'], 'tool failed')
        if part['tool'] == 'read':
            name = state['input']['filePath']
            need(state['metadata']['display']['text'] == fixture(name).decode().strip(), 'tool read differs')
            need(path_key(state['metadata']['display']['path']) == path_key(workspace + '/' + name), 'read target differs')
        else:
            need(path_key(state['metadata']['filediff']['file']) == path_key(workspace + '/labels.mjs'), 'edit target differs')
            need('-  return label;\n+  return label.trim();' in state['metadata']['diff'], 'tool edit diff differs')
    patches = [p for p in parts if p['type'] == 'patch']
    need(len(patches) == 1 and [path_key(p) for p in patches[0]['files']] == [path_key(workspace + '/labels.mjs')], 'selected patch paths differ')
    trees = read(root / 'snapshot-trees.json')
    contents = {key: tree_contents(trees, key, workspace) for key in trees}
    for part in parts:
        if part.get('snapshot'):
            need(part['snapshot'] in contents, 'missing step snapshot')
    preimage = patches[0]['hash']
    need(contents[preimage] == expected(case, 'r0'), 'patch preimage differs from baseline')
    need(contents[initial[-1]['parts'][-1]['snapshot']] == expected(case, 'r1'), 'final step snapshot differs')
    reverted = api('first-revert', 'POST', '/session/' + sid + '/revert', {'messageID': target})
    restored = api('unrevert', 'POST', '/session/' + sid + '/unrevert', {})
    marker = infos['r3'].get('revert')
    need(marker and marker['messageID'] == target and not marker.get('partID'), 'wrong recovery target')
    need(reverted['id'] == sid and reverted['revert'] == marker, 'revert response differs from subsequent state')
    need(contents[marker['snapshot']] == expected(case, 'r2'), 'pre-undo snapshot differs from actual pre-undo files')
    need(all(not infos[s].get('revert') for s in ('r0', 'r1', 'r2', 'r4')) and not restored.get('revert'), 'marker lifetime differs')
    need(restored['id'] == sid, 'unrevert returned wrong session')
    need((root / 'r3' / 'labels.mjs').read_bytes() == contents[preimage]['labels.mjs'], 'restoration did not match selected blob')
    need(all((root / 'r4' / n).read_bytes() == contents[marker['snapshot']][n] for n in FILES), 'unrevert differs from saved tree')
    # Proposals, feedback and real stored operations must agree, in order.
    request_paths = sorted(root.glob('request-*.json'))
    need(len(request_paths) == len(list(root.glob('response-*.json'))), 'request/response count differs')
    proposals, reports, main_count, auxiliary_count = [], [], 0, 0
    for index, path in enumerate(request_paths, 1):
        need(path.name == f'request-{index:02}.json', 'provider request gap')
        request, response = read(path), read(root / f'response-{index:02}.json')
        body, headers = request['body'], request['headers']
        need(request['path'] == '/v1/chat/completions' and body['model'] == 'scripted', 'provider routing differs')
        tools = {t['function']['name'] for t in body.get('tools', [])}
        main = bool(tools)
        need(response['kind'] == ('main' if main else 'auxiliary'), 'provider request classification differs')
        if main:
            main_count += 1
            need(headers.get('x-session-id') == headers.get('x-session-affinity') == sid and not headers.get('x-parent-session-id'), 'provider identity differs')
            replies = [m for m in body['messages'] if m['role'] == 'tool']
            need([r['tool_call_id'] for r in replies] == [c[0] for c in CALLS[:main_count - 1]], 'feedback order differs')
            for reply in replies:
                need(reply['content'] == by_call[reply['tool_call_id']]['state']['output'], 'feedback differs from actual tool record')
            for proposal in response['message'].get('tool_calls', []):
                fn = proposal['function']
                need(fn['name'] in tools and response['finish_reason'] == 'tool_calls', 'invalid proposal')
                proposals.append((proposal['id'], fn['name'], json.loads(fn['arguments'])))
            if not response['message'].get('tool_calls'):
                need(response['finish_reason'] == 'stop', 'abnormal report finish')
                reports.append(response['message']['content'])
        else:
            auxiliary_count += 1
            need(not response['message'].get('tool_calls'), 'auxiliary tool call')
        a, b = event('provider_request', request=index), event('provider_response', request=index)
        need(event('coding_start')['order'] < a['order'] < b['order'] < event('coding_return')['order'], 'provider traffic outside coding interval')
    need(proposals == CALLS and reports == [FINAL] and main_count == 4, 'provider sequence differs')
    need(checkpoints['r0']['provider_requests'] == 0, 'provider ran before coding')
    need(all(checkpoints[s]['provider_requests'] == len(request_paths) for s in stages if s != 'r0'), 'provider activity during recovery')
    writes = [e for e in sequence if e['kind'] == 'external_write']
    need([e['path'] for e in writes] == (['notes.txt', 'labels.mjs'] if case == 'same-file' else ['notes.txt']), 'later writer set differs')
    need(all(checkpoints['r1']['order'] < e['order'] < checkpoints['r2']['order'] for e in writes), 'later writes occurred in wrong interval')
    order = [checkpoints['r0']['order'], event('coding_start')['order'], event('coding_return')['order'],
             checkpoints['r1']['order'], checkpoints['r2']['order'], event('api_request', stem='first-revert')['order'],
             event('api_return', stem='first-revert')['order'], checkpoints['r3']['order'],
             event('api_request', stem='unrevert')['order'], event('api_return', stem='unrevert')['order'],
             checkpoints['r4']['order'], event('primary_complete')['order']]
    need(order == sorted(set(order)), 'primary event ordering differs')
    result = {'case': case, 'stages': {s: stage_results[s] for s in STAGES}, 'selected_paths': ['labels.mjs'],
              'preimage_tree': preimage, 'pre_undo_tree': marker['snapshot'],
              'provider_requests': {'main': main_count, 'auxiliary': auxiliary_count, 'recovery': 0},
              'original_messages': len(initial), 'original_parts': len(parts), 'stored_records_retained_through_unrevert': True}
    if include_continuation:
        cr = api('continuation-revert', 'POST', '/session/' + sid + '/revert', {'messageID': target})
        cm = api('continuation-message', 'POST', '/session/' + sid + '/message',
                 {'noReply': True, 'parts': [{'type': 'text', 'text': CONTINUATION}]})
        need(cr['revert'] == infos['c0']['revert'] and cr['revert']['messageID'] == target, 'continuation revert differs')
        need(contents[cr['revert']['snapshot']] == expected(case, 'r4'), 'continuation preimage differs')
        remaining = histories['c1']
        need(len(remaining) == 1 and remaining[0] == cm and cm['info']['role'] == 'user', 'new user message differs')
        need(cm['info']['id'] not in {m['info']['id'] for m in initial}, 'old message survived cleanup')
        need([p['text'] for p in cm['parts']] == [CONTINUATION] and not infos['c1'].get('revert'), 'cleanup result differs')
        need(event('primary_complete')['order'] < event('api_request', stem='continuation-revert')['order'] < checkpoints['c0']['order']
             < event('api_request', stem='continuation-message')['order'] < checkpoints['c1']['order'], 'continuation ordering differs')
        result['continuation'] = {'stages': {s: stage_results[s] for s in ('c0', 'c1')},
            'old_messages_before': len(histories['c0']), 'old_messages_after': 0, 'new_user_messages': 1,
            'marker_before': True, 'marker_after': False, 'provider_requests': 0, 'no_reply': True}
    return result

def reconstruct(root, include_continuation=False):
    meta = read(root / 'run.json')
    need(meta['schema_version'] == 1 and meta['release'] == 'v1.18.30' and meta['commit'] == PIN, 'version provenance differs')
    need(meta['binary_sha256'] == BINARY_SHA256 and meta['platform'] == 'Windows', 'runtime provenance differs')
    need(meta['cases'] == list(CASES) and meta['evidence_class'] == 'OBSERVED_WITH_SCRIPTED_PROVIDER' and meta['model_inference'] is False, 'evidence class differs')
    cases = [reconstruct_case(root / case, case, include_continuation and case == 'same-file') for case in CASES]
    need(cases[0]['preimage_tree'] == cases[1]['preimage_tree'], 'different starting tree')
    need(cases[0]['stages']['r1'] == cases[1]['stages']['r1'], 'different coding operation result')
    return {'schema_version': 1, 'runtime': meta, 'cases': cases,
            'limits': ['scripted provider; no model inference', 'Windows runtime only',
                       'existing tracked regular files at repository root', 'no concurrent writers during recovery',
                       'offline consistency is not historical authentication']}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--include-continuation', action='store_true')
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    receipt = reconstruct(args.capture.resolve(), args.include_continuation)
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print('Verified two primary recovery cases' + (' and separate noReply continuation.' if args.include_continuation else '.'))

if __name__ == '__main__':
    main()
