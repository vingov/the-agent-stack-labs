"""Corrupt private capture copies to test reconstruction. Never changes the original run."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from verify_run import reconstruct
from verify_reference import verify_report

def rewrite(value, old, new):
    if isinstance(value, str):
        return value.replace(str(old), str(new)).replace(old.as_posix(), new.as_posix())
    if isinstance(value, list):
        return [rewrite(x, old, new) for x in value]
    if isinstance(value, dict):
        return {k: rewrite(v, old, new) for k, v in value.items()}
    return value

def mutate_json(root, filename, change):
    path = root / filename
    value = json.loads(path.read_text(encoding='utf-8'))
    change(value)
    path.write_text(json.dumps(value), encoding='utf-8')

def run(source):
    controls = [
        ('missing child request', lambda r: (r / 'request-02.json').unlink()),
        ('missing barrier bytes', lambda r: (r / 'before-report/labels.mjs').unlink()),
        ('contradictory barrier bytes', lambda r: (r / 'before-report/labels.mjs').write_text('changed', encoding='utf-8')),
        ('unrelated child', lambda r: mutate_json(r, 'export-child.stdout.txt', lambda v: v['info'].update(parentID='ses_other'))),
        ('provider parent differs', lambda r: mutate_json(r, 'request-02.json', lambda v: v['headers'].update({'x-parent-session-id': 'ses_other'}))),
        ('provider input marker differs', lambda r: mutate_json(r, 'request-02.json', lambda v: v['body']['messages'].append({'role': 'user', 'content': 'PARENT_ONLY_4a86d1'}))),
        ('provider result differs', lambda r: mutate_json(r, 'request-06.json', lambda v: next(m for m in v['body']['messages'] if m['role'] == 'tool').update(content='unsupported success'))),
        ('incorrect checkpoint order', lambda r: mutate_json(r, 'sequence.json', lambda v: v[6].update(order=9))),
        ('missing policy evidence', lambda r: (r / 'cli.stderr.txt').write_text('', encoding='utf-8')),
        ('failed test process', lambda r: mutate_json(r, 'test-after.process.json', lambda v: v.update(exit=1))),
        ('changed current file', lambda r: (r / 'workspace/labels.mjs').write_text('changed', encoding='utf-8')),
        ('invented provider operation', lambda r: mutate_json(r, 'response-04.json', lambda v: v['message']['tool_calls'][0]['function'].update(arguments='{}'))),
    ]
    for label, mutation in [('unaltered copy', None), *controls]:
        with tempfile.TemporaryDirectory(prefix='opencode-p4-check-') as temp:
            target = Path(temp).resolve()
            # This unique stdlib-owned temp directory is the only cleanup target.
            assert target.parent == Path(tempfile.gettempdir()).resolve()
            for item in source.iterdir():
                if item.is_file():
                    text = item.read_text(encoding='utf-8')
                    try:
                        text = json.dumps(rewrite(json.loads(text), source, target), indent=2)
                    except json.JSONDecodeError:
                        text = text.replace(str(source), str(target)).replace(source.as_posix(), target.as_posix())
                    (target / item.name).write_text(text, encoding='utf-8')
            for folder in ['before', 'before-report', 'after']:
                shutil.copytree(source / folder, target / folder)
            (target / 'workspace').mkdir()
            for name in ['labels.mjs', 'labels.test.mjs']:
                shutil.copyfile(source / 'workspace' / name, target / 'workspace' / name)
            if mutation:
                mutation(target)
            try:
                errors = verify_report(reconstruct(target))
            except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration) as exc:
                errors = [str(exc)]
            if bool(errors) != bool(mutation):
                raise AssertionError(label + ': ' + str(errors))
            print('PASS: ' + label)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    run(parser.parse_args().run_directory.resolve())
