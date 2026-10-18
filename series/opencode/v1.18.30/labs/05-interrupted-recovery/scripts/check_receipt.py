"""Portable consistency check of the supplied synthetic receipt, not a live rerun."""
import argparse
import json
from pathlib import Path
from contract import BINARY_SHA256, CALLS, FILES, IMMUTABLE, PIN, TEST_NAMES, fixture, intended_files, sha
from evidence import acceptance, require, tree_files


def check(receipt):
    require(receipt['schema'] == 1 and receipt['source_commit'] == PIN
            and receipt['binary_sha256'] == BINARY_SHA256, 'Unexpected receipt version/pin')
    require([case['case'] for case in receipt['cases']] in
            (['normal', 'graceful'], ['normal', 'graceful', 'forced']), 'Case inventory changed')
    require(len({case['session'] for case in receipt['cases']}) == len(receipt['cases']), 'Cases share a session')
    baseline, intended = {name: fixture(name) for name in FILES}, intended_files()
    known = {name: {sha(content): content for content in (baseline[name], intended[name])} for name in FILES}
    for case in receipt['cases']:
        states, files = case['states'], {}
        trees = {ref: tree_files(ref, tree) for ref, tree in case['trees'].items()}
        for tree in trees.values():
            require(all(tree[name] == baseline[name] for name in IMMUTABLE), 'Immutable snapshot input changed')
        for stage, state in states.items():
            require(state['remote_read_available'] == (stage != 'primary' or case['case'] != 'forced'),
                    'Remote read availability contradicts the case/checkpoint')
            require(set(state['files']) == set(FILES), 'Missing artifact evidence')
            current = {}
            for name, value in state['files'].items():
                require(value['sha256'] in known[name], 'Unknown file hash: ' + name)
                current[name] = known[name][value['sha256']]
                require(value['bytes'] == len(current[name]), 'Wrong artifact length')
            require(state['tests'] == dict(zip(TEST_NAMES, acceptance(current))), 'Named tests contradict artifact bytes')
            require(state['interval'][0] <= state['file_witness_interval'][0] <= state['file_witness_interval'][1]
                    <= state['interval'][1], 'File witness lies outside its observation')
            require(set(state['snapshot_refs']) <= set(trees), 'Missing snapshot content')
            for patch in state['patches']:
                require(patch['hash'] in trees and set(patch['files']) <= set(FILES), 'Invalid patch reference/path')
            files[stage] = current
        require(files['initial'] == baseline, 'Baseline changed')
        partial = dict(intended)
        partial['catalogue.manifest.json'] = baseline['catalogue.manifest.json']
        require(files['barrier'] == partial, 'Barrier bytes do not establish an incomplete task')
        tools = states['barrier']['tools']
        require([(p['call_id'], p['tool'], p['input']) for p in tools] == CALLS
                and [p['status'] for p in tools] == ['completed'] * 5 + ['running'], 'Invalid tool barrier')
        start, end = case['intervention_interval']
        require(states['barrier']['interval'][1] <= start <= end <= states['primary']['interval'][0],
                'Intervention ordering changed')
        old_refs = case['pre_intervention_saved_catalogue_refs']
        require(old_refs and all(ref in states['barrier']['snapshot_refs']
                and case['trees'][ref]['first_stage'] == 'barrier'
                and case['trees'][ref]['end_ns'] <= start
                and trees[ref]['catalogue.json'] == baseline['catalogue.json'] for ref in old_refs),
                'Saved version was not witnessed before intervention')
        process = case['process']
        require(set(process['immediate']) == set(process['identities']) == {'server', 'shell', 'generator'},
                'Missing process evidence')
        identities = process['identities']
        require(identities['server']['image_sha256'] == BINARY_SHA256
                and identities['server']['image_basename'] == 'opencode.exe'
                and identities['shell']['image_basename'] == 'pwsh.exe'
                and identities['generator']['image_basename'] == 'node.exe', 'Unexpected process executable')
        require(0 < identities['server']['creation_time_100ns'] <= identities['shell']['creation_time_100ns']
                <= identities['generator']['creation_time_100ns'], 'Invalid process creation order')
        require(len({p['pid'] for p in identities.values()}) == 3 and all(p['pid'] > 0 for p in identities.values()),
                'Process identity inventory is invalid')
        for role, item in process['immediate'].items():
            require(type(item['alive']) is bool and (item['exit_code'] is None if item['alive'] else type(item['exit_code']) is int),
                    'Contradictory process result')
            require(end <= item['query_interval'][0] <= item['query_interval'][1] <= states['primary']['interval'][0],
                    'Process query predates intervention response')
        require(process['cleanup_start_ns'] >= states['primary']['interval'][1] and process['sample_count'] >= 2,
                'Harness cleanup contaminated primary evidence')
        exit_query = process['first_generator_exit_query_interval']
        require(process['generator_exit_observed_before_harness_cleanup'] ==
                bool(exit_query and exit_query[1] < process['cleanup_start_ns']), 'Exit attribution contradicts timeline')
        last = process['last_monitored_generator']
        require(last['end_ns'] >= states['primary']['interval'][1] and last['end_ns'] <= process['cleanup_start_ns'],
                'Process monitoring does not cover the primary observation')
        require(all(process['after_cleanup'][role]['alive'] is False for role in ('shell', 'generator')),
                'Children were not confirmed exited before restart')
        if case['case'] == 'forced':
            require(states['barrier']['tools'] == states['restarted']['tools']
                    and states['barrier']['patches'] == states['restarted']['patches'], 'Stored records changed across forced restart')
        else:
            require(states['primary']['tools'] == states['reopened']['tools'] == states['restarted']['tools']
                    and states['primary']['patches'] == states['reopened']['patches'] == states['restarted']['patches'],
                    'Stored records changed across quiescent restart')
        selection = {}
        for patch in states['restarted']['patches']:
            for name in patch['files']:
                selection.setdefault(name, patch['hash'])
        require(selection == case['selected_earliest_refs'], 'Revert selection differs from actual patch order')
        changed = sorted(name for name in FILES if files['restarted'][name] != baseline[name])
        require(changed == case['changed_paths_before_revert'] and sorted(set(changed) - set(selection)) ==
                case['unselected_changed_paths'], 'Coverage claim contradicts file/patch evidence')
        expected = dict(files['restarted'])
        for name, ref in selection.items():
            expected[name] = trees[ref][name]
        require(files['reverted'] == expected, 'Revert bytes contradict selected saved versions')
        require(case['restored_baseline'] == (files['reverted'] == baseline), 'Baseline restoration claim is false')
        require(trees[case['preundo_snapshot']] == files['restarted'] == files['unreverted']
                and case['unrevert_restored_preundo'] is True, 'Unrevert claim contradicts saved/observed bytes')
    return len(receipt['cases'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', type=Path, nargs='?', default=Path(__file__).resolve().parents[1] / 'reference' / 'receipt.json')
    args = parser.parse_args()
    print('Consistent reference cases:', check(json.loads(args.receipt.read_text(encoding='utf-8'))))
