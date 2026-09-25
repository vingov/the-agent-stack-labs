"""Independently compare a private run receipt with raw HTTP captures, exports and files."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from verify_reference import verify


def markers(value):
    return set(re.findall(r'\bLAB_P2_([A-Z_]+)\b', value if isinstance(value, str) else json.dumps(value)))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def verify_run(root):
    report = json.loads((root / 'receipt.json').read_text(encoding='utf-8'))
    errors = verify(report)
    def check(condition, label):
        if not condition:
            errors.append(label)
    for case in report['cases']:
        folder = root / case['mode']
        raw_requests = sorted(folder.glob('request-*.json'))
        check(len(raw_requests) == len(case['requests']), 'raw request inventory')
        for raw_path, req in zip(raw_requests, case['requests']):
            raw = json.loads(raw_path.read_text(encoding='utf-8'))
            check(len(raw['messages']) == len(req['messages']), 'raw message count')
            for actual, recorded in zip(raw['messages'], req['messages']):
                content = actual.get('content')
                data = (content if isinstance(content, str) else json.dumps(content, sort_keys=True)).encode()
                check(actual['role'] == recorded['role'], 'raw role')
                check(markers(content) == set(recorded['markers']), 'raw markers')
                check(digest(data) == recorded['content_sha256'], 'raw content hash')
                check(actual.get('tool_call_id') == recorded['tool_call_id'], 'raw tool result ID')
                check([t['id'] for t in actual.get('tool_calls', [])] == recorded['tool_calls'], 'raw assistant tool IDs')
        export = json.loads((folder / 'export-3.json').read_text(encoding='utf-8'))
        check(export['info']['id'] == case['session_id'], 'export session ID')
        check([m['info']['id'] for m in export['messages']] == [m['id'] for m in case['messages']], 'durable message inventory')
        recorded_parts = {p['id']: p for m in case['messages'] for p in m['parts']}
        for msg in export['messages']:
            for part in msg['parts']:
                recorded = recorded_parts[part['id']]
                if part['type'] == 'text':
                    check(markers(part['text']) == set(recorded['markers']), 'durable text markers')
                if part['type'] == 'compaction':
                    check(part.get('tail_start_id') == recorded['tail_start_id'], 'durable tail boundary')
                if part['type'] == 'tool':
                    check(part['callID'] == recorded['call_id'], 'durable tool identity')
                    check(markers(part['state'].get('output', '')) == set(recorded['output_markers']), 'durable output markers')
                    check(digest(part['state'].get('output', '').encode()) == recorded['output_sha256'], 'durable output hash')
        for filename, recorded in case['current_files'].items():
            actual = (folder / 'workspace' / filename).read_bytes()
            check(digest(actual) == recorded['sha256'], 'current file hash: ' + filename)
            check(markers(actual.decode()) == set(recorded['markers']), 'current file markers: ' + filename)
        for call in case['calls']:
            events = [json.loads(line) for line in (folder / f"cli-{call['stage']}.stdout.jsonl").read_text(encoding='utf-8').splitlines() if line.startswith('{')]
            check({e['sessionID'] for e in events if 'sessionID' in e} == {case['session_id']}, 'CLI session identity')
            check(not any(e.get('type') == 'error' for e in events), 'CLI error event')
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    try:
        errors = verify_run(args.run_directory)
    except (OSError, ValueError, KeyError, TypeError) as error:
        errors = ['Missing or malformed raw evidence: ' + str(error)]
    print(json.dumps({'passed': not errors, 'errors': errors}, indent=2))
    raise SystemExit(bool(errors))
