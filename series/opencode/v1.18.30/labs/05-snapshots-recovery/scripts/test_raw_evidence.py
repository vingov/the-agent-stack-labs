"""Reject altered copies of actual private captures; never mutate the originals."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from verify_run import read, reconstruct

def mutate_json(path, change):
    value = read(path)
    change(value)
    path.write_text(json.dumps(value), encoding='utf-8')

def drop_preimage(root):
    messages = read(root / 'r1-messages.response.json')
    key = next(p['hash'] for m in messages for p in m['parts'] if p['type'] == 'patch')
    mutate_json(root / 'snapshot-trees.json', lambda d: d.pop(key))

def reorder_writer(root):
    def move(events):
        writer = next(e for e in events if e['kind'] == 'external_write')
        events.remove(writer)
        events.insert(0, writer)
        for index, event in enumerate(events, 1):
            event['order'] = index
    mutate_json(root / 'sequence.json', move)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    original = args.capture.resolve()
    reconstruct(original, True)
    mutations = [
        ('missing preimage', drop_preimage),
        ('corrupt tree bytes', lambda p: mutate_json(p / 'snapshot-trees.json', lambda d: d[next(iter(d))].update(object_base64='AA=='))),
        ('corrupt blob bytes', lambda p: mutate_json(p / 'snapshot-trees.json', lambda d: d[next(iter(d))]['files']['labels.mjs'].update(base64='AA=='))),
        ('wrong revert target', lambda p: mutate_json(p / 'first-revert.request.json', lambda d: d['payload'].update(messageID='wrong-message'))),
        ('changed fixed tests', lambda p: (p / 'r3' / 'labels.test.mjs').write_text('// altered\n')),
        ('wrong later-write order', reorder_writer),
        ('wrong operation owner', lambda p: mutate_json(p / 'r1-messages.response.json', lambda d: d[1]['parts'][1].update(sessionID='wrong-session'))),
        ('missing test output', lambda p: (p / 'r3-test.stdout.txt').unlink()),
        ('wrong test counts', lambda p: (p / 'r3-test.stdout.txt').write_text('ℹ tests 4\nℹ pass 4\nℹ fail 0\nℹ cancelled 0\nℹ skipped 0\nℹ todo 0\n', encoding='utf-8')),
        ('wrong patch path', lambda p: mutate_json(p / 'r1-messages.response.json', lambda d: next(part for m in d for part in m['parts'] if part['type'] == 'patch').update(files=['notes.txt']))),
        ('altered proposal', lambda p: mutate_json(p / 'response-03.json', lambda d: d['message']['tool_calls'][0]['function'].update(arguments='{}'))),
        ('missing provider request', lambda p: (p / 'request-03.json').unlink()),
        ('wrong server route', lambda p: mutate_json(p / 'first-revert.request.json', lambda d: d.update(url=d['url'].replace('/session/', '/api/session/')))),
        ('old history after continuation', lambda p: shutil.copyfile(p / 'c0-messages.response.json', p / 'c1-messages.response.json')),
    ]
    ignore = shutil.ignore_patterns('workspace', 'home', 'config', 'data', 'cache', 'state', 'temp', 'hooks')
    with tempfile.TemporaryDirectory(prefix='recovery-evidence-check-') as temporary:
        base = Path(temporary)
        positive = base / 'positive'
        shutil.copytree(original, positive, ignore=ignore)
        reconstruct(positive, True)
        # The primary comparison remains independently checkable without continuation.
        for pattern in ('c0-*', 'c1-*', 'continuation-*'):
            for path in (positive / 'same-file').glob(pattern):
                path.unlink()
        reconstruct(positive, False)
        for index, (name, change) in enumerate(mutations):
            copy = base / str(index)
            shutil.copytree(original, copy, ignore=ignore)
            change(copy / 'same-file')
            try:
                reconstruct(copy, True)
            except (ValueError, KeyError, FileNotFoundError):
                print('Rejected: ' + name)
            else:
                raise AssertionError('Accepted corrupt evidence: ' + name)
    print(f'Unmodified copies passed; {len(mutations)} corruption controls rejected.')

if __name__ == '__main__':
    main()
