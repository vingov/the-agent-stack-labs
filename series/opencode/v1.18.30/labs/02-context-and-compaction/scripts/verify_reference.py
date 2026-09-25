"""Check evidence relationships, not a saved passed flag; no execution authentication."""
import argparse
import json
import re
from pathlib import Path


def request_marks(request):
    return {marker for message in request['messages'] for marker in message['markers']}


def verify(report):
    errors = []
    def check(condition, label):
        if not condition:
            errors.append(label)
    try:
        check(report['schema_version'] == 1, 'schema version')
        check(report['release'] == '1.18.30', 'release')
        check(report['commit'] == '3104c1428ec91f809e5ab86631300de41eb6952e', 'commit')
        check(report['evidence_class'] == 'OBSERVED_WITH_SCRIPTED_PROVIDER', 'evidence class')
        check(bool(re.fullmatch('[0-9a-f]{64}', report['binary_sha256'])), 'binary digest')
        check(len(report['cases']) == 2, 'two cases only')
        check({c['mode'] for c in report['cases']} == {'compact', 'no_compact'}, 'case pair')
        for case in report['cases']:
            mode = case['mode']
            def need(condition, label):
                check(condition, mode + ': ' + label)
            need(case['config'] == {'auto': mode == 'compact', 'prune': False,
                                   'tail_turns': 1, 'preserve_recent_tokens': 8000}, 'configuration')
            need([c['stage'] for c in case['calls']] == [1, 2, 3], 'three CLI stages')
            need(all(c['exit'] == 0 and not c['errors'] for c in case['calls']), 'CLI success')
            need(all(c['session_id'] == case['session_id'] for c in case['calls']), 'one session across stages')
            reqs = case['requests']
            ordinary = [r for r in reqs if r['kind'] == 'ordinary']
            by_stage = {s: [r for r in ordinary if r['stage'] == s] for s in [1, 2, 3]}
            need([len(by_stage[s]) for s in [1, 2, 3]] == ([2, 3, 2] if mode == 'compact' else [2, 2, 2]), 'request counts')
            first = request_marks(by_stage[1][0])
            need({'GLOBAL_RULE', 'ROOT_RULE', 'CONFIG_RULE', 'ATTACHED_NOTE', 'OLD_REQUEST'} <= first, 'initial inclusion')
            need(not {'OLD_FILE', 'NESTED_RULE', 'FALLBACK_RULE', 'UNREAD_SECRET'} & first, 'initial exclusion')
            need({'OLD_FILE', 'OLD_END', 'NESTED_RULE'} <= request_marks(by_stage[1][1]), 'read feedback')
            stale = by_stage[2][0]
            need('OLD_FILE' in request_marks(stale) and 'NEW_FILE' not in request_marks(stale), 'stale observation')
            need(stale['file_markers_at_request'] == ['NEW_FILE'], 'new bytes already on disk')
            need(stale['file_sha256_at_request'] == case['current_files']['src/slug.mjs']['sha256'], 'current file hash')
            need(by_stage[1][0]['file_sha256_at_request'] == by_stage[1][1]['file_sha256_at_request'] != stale['file_sha256_at_request'], 'external file change')
            need(by_stage[2][1]['response_usage'] == 31000, 'controlled high usage')
            need(all(not {'UNREAD_SECRET', 'FALLBACK_RULE'} & request_marks(r) for r in reqs), 'negative controls')
            compact = [r for r in reqs if r['kind'] == 'compaction']
            before_reread = request_marks(by_stage[3][0])
            if mode == 'compact':
                need(len(compact) == 1, 'one compaction request')
                head = request_marks(compact[0])
                need({'OLD_REQUEST', 'OLD_FILE', 'ATTACHED_NOTE'} <= head, 'summary head evidence')
                need(not {'OLD_END', 'NESTED_RULE', 'TAIL_REQUEST', 'TAIL_FILE'} & head, 'summary clipping and tail exclusion')
                continuation = request_marks(by_stage[2][2])
                need({'SUMMARY_NOTE', 'TAIL_REQUEST', 'TAIL_FILE', 'ROOT_RULE'} <= continuation, 'summary and retained tail')
                need(not {'OLD_REQUEST', 'OLD_FILE', 'OLD_END', 'NESTED_RULE', 'ATTACHED_NOTE'} & continuation, 'head excluded from continuation')
                need('SUMMARY_NOTE' in before_reread and 'OLD_FILE' not in before_reread, 'next invocation uses projection')
            else:
                need(not compact, 'disabled control has no compaction')
                need({'OLD_FILE', 'OLD_END', 'NESTED_RULE', 'OLD_REQUEST'} <= before_reread, 'disabled control keeps head')
                need('SUMMARY_NOTE' not in before_reread, 'disabled control has no summary')
            need('NEW_FILE' not in before_reread, 'changed file needs re-observation')
            need({'NEW_FILE', 'NESTED_RULE'} <= request_marks(by_stage[3][1]), 'reread feedback')
            tools = [p for m in case['messages'] for p in m['parts'] if p['type'] == 'tool']
            need([p['call_id'] for p in tools] == [e['id'] for e in case['emitted']], 'durable/emitted call identities')
            need(len(tools) == 3 and all(p['status'] == 'completed' for p in tools), 'three completed real reads')
            need({'OLD_FILE', 'OLD_END', 'NESTED_RULE'} <= set(tools[0]['output_markers']), 'old output remains durable')
            need(not any(p['compacted'] for p in tools), 'no pruning in this experiment')
            need(tools[0]['loaded'] == ['src/AGENTS.md'], 'nested instruction provenance')
            need(tools[2]['loaded'] == (['src/AGENTS.md'] if mode == 'compact' else []), 'instruction rediscovery follows selected history')
            for tool in tools:
                feedback = [m for r in reqs for m in r['messages'] if m['tool_call_id'] == tool['call_id']]
                need(bool(feedback), 'tool result reaches provider: ' + tool['call_id'])
                need(all(m['role'] == 'tool' and m['content_sha256'] == tool['output_sha256']
                         and m['markers'] == tool['output_markers'] for m in feedback),
                     'persisted output equals provider feedback: ' + tool['call_id'])
                need(any(tool['call_id'] in m['tool_calls'] for r in reqs for m in r['messages']), 'matching assistant tool call')
            summaries = [m for m in case['messages'] if m['summary']]
            parts = [p for m in case['messages'] for p in m['parts'] if p['type'] == 'compaction']
            if mode == 'compact':
                need(len(summaries) == len(parts) == 1, 'durable compaction records')
                tail = next(m for m in case['messages'] if any('TAIL_REQUEST' in p.get('markers', []) for p in m['parts']))
                need(parts[0]['tail_start_id'] == tail['id'], 'tail boundary is recent user message')
                parent = next(m for m in case['messages'] if any(p['type'] == 'compaction' for p in m['parts']))
                need(summaries[0]['parent_id'] == parent['id'], 'summary parent is compaction message')
                need(summaries[0]['finish'] == 'stop', 'completed summary')
                need(any('SUMMARY_NOTE' in p.get('markers', []) for p in summaries[0]['parts']), 'scripted summary persisted')
            else:
                need(not summaries and not parts, 'no stored compaction in control')
            need(case['current_files']['unread.txt']['markers'] == ['UNREAD_SECRET'], 'unread file exists')
            need(any(m.get('tokens', {}).get('input') == 31000 for m in case['messages'] if m.get('tokens')), 'reported usage persisted')
    except (KeyError, TypeError, IndexError, StopIteration, AttributeError) as error:
        errors.append('Missing or malformed evidence: ' + str(error))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', nargs='?', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'reference-results/windows-2026-09-25/receipt.json')
    args = parser.parse_args()
    try:
        errors = verify(json.loads(args.receipt.read_text(encoding='utf-8')))
    except (OSError, ValueError) as error:
        errors = [str(error)]
    print(json.dumps({'passed': not errors, 'errors': errors}, indent=2))
    raise SystemExit(bool(errors))


if __name__ == '__main__':
    main()
