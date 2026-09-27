"""Reject altered raw evidence in temporary copies of an actual private run."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import tempfile
from verify_run import verify_run


def run_controls(original):
    errors = verify_run(original)
    if errors:
        raise AssertionError('Original run must verify first: ' + repr(errors))
    # Copy only evidence needed by the checker, not databases/caches or the Git directory.
    with tempfile.TemporaryDirectory(prefix='raw-evidence-controls-', dir=original.parent) as name:
        root = Path(name)
        shutil.copyfile(original / 'receipt.json', root / 'receipt.json')
        for mode in ['compact', 'no_compact']:
            target = root / mode
            target.mkdir()
            shutil.copytree(original / mode / 'workspace', target / 'workspace',
                            ignore=shutil.ignore_patterns('.git'))
            for pattern in ['request-*.json', 'export-3.json', 'cli-*.stdout.jsonl']:
                for path in (original / mode).glob(pattern):
                    shutil.copyfile(path, target / path.name)
        assert not verify_run(root), 'Copied evidence must verify before mutation'
        export_path = root / 'compact/export-3.json'
        original_export = json.loads(export_path.read_text(encoding='utf-8'))

        def tool(export):
            return next(p for m in export['messages'] for p in m['parts'] if p['type'] == 'tool')

        def summary(export):
            return next(m['info'] for m in export['messages'] if m['info'].get('summary') is True)

        controls = {
            'loaded instructions': lambda e: tool(e)['state']['metadata'].update(loaded=[]),
            'compacted mark': lambda e: tool(e)['state']['time'].update(compacted=1),
            'tool status': lambda e: tool(e)['state'].update(status='error'),
            'summary flag': lambda e: summary(e).update(summary=False),
            'summary parent': lambda e: summary(e).update(parentID='wrong'),
            'summary role': lambda e: summary(e).update(role='user'),
            'summary finish': lambda e: summary(e).update(finish='error'),
            'reported usage': lambda e: next(m['info'] for m in e['messages'] if m['info'].get('tokens', {}).get('input') == 31000)['tokens'].update(input=0),
        }
        for name, mutate in controls.items():
            altered = copy.deepcopy(original_export)
            mutate(altered)
            export_path.write_text(json.dumps(altered), encoding='utf-8')
            if not verify_run(root):
                raise AssertionError('Accepted contradictory raw ' + name)
            print('Rejected raw ' + name)
        shutil.copyfile(original / 'compact/export-3.json', export_path)
        capture = root / 'compact/request-06.json'
        request = json.loads(capture.read_text(encoding='utf-8'))
        next(m for m in request['messages'] if 'LAB_P2_SUMMARY_NOTE' in str(m))['content'] = 'contradictory capture'
        capture.write_text(json.dumps(request), encoding='utf-8')
        assert verify_run(root), 'Accepted contradictory raw capture'
        print('Rejected raw capture content')
        capture.unlink()
        assert verify_run(root), 'Accepted missing raw capture'
        print('Rejected missing raw capture')
    return len(controls) + 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    count = run_controls(args.run_directory.resolve())
    print(f'PASS: {count} raw-evidence corruption controls; original evidence unchanged')
