"""Corrupt private receipts in memory and require the raw verifier to reject them."""
import argparse
import base64
import json
from pathlib import Path
from evidence import EvidenceError, verify


def run(root, implementation=None):
    root = Path(root)
    verify(root, implementation)
    changes = []

    def mutate(label, name, edit):
        value = json.loads((root / name).read_bytes())
        edit(value)
        changes.append((label, {name: json.dumps(value).encode()}))

    mutate('wrong session', 'graceful/identity.json', lambda v: v.update(session='ses_wrong'))
    mutate('wrong API directory', 'graceful/abort.request.json', lambda v: v.update(workspace='C:\\unrelated'))
    mutate('wrong recovery boundary', 'graceful/first-revert.request.json', lambda v: v['payload'].update(messageID='msg_wrong'))
    mutate('failed process query', 'graceful/immediate-post-intervention.processes.json',
           lambda v: v['processes']['generator'].update(wait_result=4294967295))
    mutate('process identity reuse', 'graceful/immediate-post-intervention.processes.json',
           lambda v: v['processes']['generator'].update(creation_time_100ns=1))
    mutate('missing process', 'graceful/immediate-post-intervention.processes.json', lambda v: v['processes'].pop('generator'))
    mutate('changed test bytes', 'graceful/barrier-before-test.files.json',
           lambda v: v['files']['acceptance.test.mjs'].update(base64=base64.b64encode(b'// no tests').decode()))
    mutate('changed helper bytes', 'graceful/barrier-before-test.files.json',
           lambda v: v['files']['generate-catalogue.mjs'].update(sha256='0' * 64))
    mutate('late barrier write', 'graceful/barrier-before-test.files.json', lambda v: v.update(end_ns=10**20))
    mutate('late abort response', 'graceful/abort.http.json', lambda v: v.update(end_ns=10**20))
    mutate('different restart profile', 'graceful/server-2.launch.json', lambda v: v.update(profile_sha256='0' * 64))

    def terminal(v):
        next(p for m in v for p in m['parts'] if p.get('callID') == 'generate_catalogue')['state']['status'] = 'completed'
    mutate('terminal barrier tool', 'graceful/barrier-messages.response.json', terminal)

    def corrupt_tree(v):
        next(iter(v.values()))['object_base64'] = base64.b64encode(b'not a tree').decode()
    mutate('corrupt saved object', 'graceful/snapshot-trees.json', corrupt_tree)
    mutate('missing saved object', 'graceful/snapshot-trees.json', lambda v: v.pop(next(iter(v))))
    mutate('retrospective saved object', 'graceful/snapshot-trees.json', lambda v: next(iter(v.values())).update(first_stage='reverted'))

    def patch_path(v):
        next(p for m in v for p in m['parts'] if p['type'] == 'patch')['files'] = ['C:\\outside\\labels.mjs']
    mutate('patch escapes fixture', 'graceful/restarted-messages.response.json', patch_path)
    mutate('cleanup before observation', 'graceful/events.json',
           lambda v: next(e for e in v if e['kind'] == 'control_marker_start' and e['name'] == 'stop.json').update(time_ns=0))
    changes.append(('swapped case messages', {'graceful/barrier-messages.response.json':
                    (root / 'normal/barrier-messages.response.json').read_bytes()}))
    name = 'graceful/barrier-acceptance.stdout'
    changes.append(('contradictory TAP', {name: (root / name).read_bytes().replace(b'not ok 6', b'ok 6')}))
    for label, overrides in changes:
        try:
            verify(root, implementation, overrides)
        except (EvidenceError, KeyError, ValueError) as error:
            print('REJECTED:', label, '-', str(error))
        else:
            raise AssertionError('Verifier accepted negative control: ' + label)
    return len(changes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--implementation', type=Path)
    args = parser.parse_args()
    print('Rejected controls:', run(args.capture, args.implementation))
