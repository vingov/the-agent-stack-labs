"""Reject contradictory public receipts and optional private capture copies."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import tempfile
from boundary_contract import CASES, LAB
from test_raw_evidence import mutate_json, rewrite
from verify_boundary_reference import verify
from verify_boundary_run import reconstruct

def rejected(check):
    try:
        check()
    except (OSError, ValueError, KeyError, TypeError, IndexError, StopIteration):
        return True
    return False

def public_controls(receipt):
    controls = [
        ('missing comparison', lambda x: x['results'].pop()),
        ('wrong pin', lambda x: x.update(commit='wrong')),
        ('claims inference', lambda x: x.update(model_inference=True)),
        ('wrong entrypoint', lambda x: x.update(entrypoint='local run')),
        ('parent role widened', lambda x: x['results'][2]['role_configuration']['coordinator']['permission']['edit'].update({'labels.mjs':'allow'})),
        ('session deny dropped', lambda x: x['results'][3]['sessions']['child']['permission'].pop(3)),
        ('denied child invented', lambda x: x['results'][5].update(child_count=1)),
        ('gate outcome altered', lambda x: x['results'][3]['evaluations'][-1].update(action='allow')),
        ('operation changed', lambda x: x['results'][2]['operations'][-1]['arguments'].update(filePath='other.mjs')),
        ('operation status altered', lambda x: x['results'][3]['operations'][-1].update(status='completed')),
        ('file outcome altered', lambda x: x['results'][2]['files']['after'].update({'labels.mjs':'wrong'})),
        ('tests weakened', lambda x: x['results'][2]['checks']['after'].update(tests=3)),
        ('parent context copied', lambda x: x['results'][2]['requests'][1]['markers'].update(parent=True)),
        ('report replaced', lambda x: x['results'][2].update(selected_report='unsupported')),
        ('child history copied', lambda x: x['results'][2]['requests'][-1]['markers'].update(observation=True)),
        ('tool hidden', lambda x: x['results'][2]['requests'][3].update(tools=[])),
        ('effective rule omitted', lambda x: x['results'][2]['resolved_relevant_role_rules'].update(parent=[])),
        ('ask substituted', lambda x: x['results'][3].update(pending_asks=1)),
    ]
    verify(receipt)
    for label, change in controls:
        candidate = copy.deepcopy(receipt)
        change(candidate)
        if not rejected(lambda: verify(candidate)):
            raise AssertionError('accepted corruption: ' + label)
    print('PASS: valid public receipt and ' + str(len(controls)) + ' contradictory receipt controls.')

def private_controls(source):
    controls = [
        ('missing request', lambda r: (r / 'parent-role/request-02.json').unlink()),
        ('wrong role config', lambda r: mutate_json(r, 'parent-role/resolved-parent.stdout.txt', lambda x: x['permission'].append({'permission':'edit','pattern':'labels.mjs','action':'allow'}))),
        ('missing session deny', lambda r: mutate_json(r, 'parent-session/export-child.json', lambda x: x['info']['permission'].pop(3))),
        ('wrong child relation', lambda r: mutate_json(r, 'parent-role/export-child.json', lambda x: x['info'].update(parentID='other'))),
        ('unexpected child', lambda r: mutate_json(r, 'dispatch/children.json', lambda x: x.append({'id':'other'}))),
        ('parent marker in child', lambda r: mutate_json(r, 'parent-role/request-02.json', lambda x: x['body']['messages'].append({'role':'user','content':'PARENT_ONLY_4a86d1'}))),
        ('false tool feedback', lambda r: mutate_json(r, 'parent-role/request-06.json', lambda x: next(m for m in x['body']['messages'] if m['role']=='tool').update(content='unsupported'))),
        ('wrong provider report', lambda r: mutate_json(r, 'parent-role/response-05.json', lambda x: x['message'].update(content='unsupported'))),
        ('unfinished provider report', lambda r: mutate_json(r, 'parent-role/response-05.json', lambda x: x.update(finish_reason='length'))),
        ('actual file changed', lambda r: (r / 'parent-role/workspace/labels.mjs').write_text('changed', encoding='utf-8')),
        ('test process failed', lambda r: mutate_json(r, 'parent-role/test-after.process.json', lambda x: x.update(exit=1))),
        ('missing policy log', lambda r: (r / 'parent-session/server.stderr.txt').write_text('', encoding='utf-8')),
        ('different tool proposal', lambda r: mutate_json(r, 'parent-role/response-04.json', lambda x: x['message']['tool_calls'][0]['function'].update(arguments='{}'))),
        ('wrong create policy', lambda r: mutate_json(r, 'parent-session/session-create-input.json', lambda x: x.update(permission=[]))),
        ('wrong checkpoint order', lambda r: mutate_json(r, 'parent-role/sequence.json', lambda x: x[4].update(order=99))),
        ('different read target', lambda r: mutate_json(r, 'parent-role/export-child.json', lambda x: next(p for m in x['messages'] for p in m['parts'] if p.get('callID') == 'child_read_helper')['state']['metadata']['display'].update(path='other.mjs'))),
        ('different edit target', lambda r: mutate_json(r, 'parent-role/export-child.json', lambda x: next(p for m in x['messages'] for p in m['parts'] if p.get('callID') == 'child_edit')['state']['metadata']['filediff'].update(file='other.mjs'))),
        ('different assistant workspace', lambda r: mutate_json(r, 'parent-role/export-child.json', lambda x: next(m for m in x['messages'] if m['info']['role'] == 'assistant')['info']['path'].update(cwd='elsewhere'))),
    ]
    for label, change in [('unaltered copy', None), *controls]:
        with tempfile.TemporaryDirectory(prefix='opencode-boundary-check-') as temp:
            target = Path(temp).resolve()
            assert target.parent == Path(tempfile.gettempdir()).resolve()
            for directory in [source, *[source / case for case in CASES]]:
                dest = target / directory.relative_to(source)
                dest.mkdir(exist_ok=True)
                for item in directory.iterdir():
                    if not item.is_file():
                        continue
                    text = item.read_text(encoding='utf-8')
                    try:
                        text = json.dumps(rewrite(json.loads(text), source, target))
                    except json.JSONDecodeError:
                        lines = []
                        for line in text.splitlines():
                            try:
                                lines.append(json.dumps(rewrite(json.loads(line), source, target)))
                            except json.JSONDecodeError:
                                lines.append(line.replace(str(source), str(target)).replace(source.as_posix(), target.as_posix()))
                        text = '\n'.join(lines) + '\n'
                    (dest / item.name).write_text(text, encoding='utf-8')
                if directory != source:
                    for folder in ('before', 'before-report', 'after'):
                        if (directory / folder).exists():
                            shutil.copytree(directory / folder, dest / folder)
                    (dest / 'workspace').mkdir()
                    for name in ('labels.mjs', 'labels.test.mjs'):
                        shutil.copyfile(directory / 'workspace' / name, dest / 'workspace' / name)
            if change:
                change(target)
            if rejected(lambda: verify(reconstruct(target))) != bool(change):
                raise AssertionError('unexpected verification result: ' + label)
    print('PASS: unaltered private copy and ' + str(len(controls)) + ' corrupted private capture controls.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', type=Path, default=LAB / 'reference-results/windows-2026-10-10-boundary/receipt.json')
    parser.add_argument('--raw', type=Path)
    args = parser.parse_args()
    public_controls(json.loads(args.receipt.read_text(encoding='utf-8')))
    if args.raw:
        private_controls(args.raw.resolve())
