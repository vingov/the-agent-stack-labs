"""Collect a fresh private Windows interruption experiment; verify it separately."""
import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import uuid

from capture import Recorder, write_json
from contract import BINARY_SHA256, CALLS, CASES, FILES, LAB, PIN, PROMPT, fixture, intended_files, roles, sha
from provider import ScriptedProvider
from winprocess import Process, bind_generator


class Monitor:
    def __init__(self, recorder, processes):
        self.recorder, self.processes = recorder, processes
        self.stop_event = threading.Event()
        self.error = None
        self.path = recorder.root / 'process-samples.jsonl'
        self.sample()
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def sample(self):
        value = {name: process.observe() for name, process in self.processes.items()}
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value) + '\n')

    def run(self):
        try:
            while not self.stop_event.wait(.04):
                self.sample()
        except Exception as error:
            self.error = repr(error)
            self.recorder.event('process_monitor_error', error=self.error)

    def close(self):
        self.stop_event.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive() or self.error:
            raise RuntimeError('Process monitor failed: ' + str(self.error))
        self.sample()


def run_case(root, case, cli, node, shell):
    root.mkdir()
    workspace = root / 'workspace'
    workspace.mkdir()
    for name in FILES:
        (workspace / name).write_bytes(fixture(name))
    for name in ('home', 'config', 'data', 'cache', 'state', 'temp', 'hooks', 'control'):
        (root / name).mkdir()
    nonce = uuid.uuid4().hex
    env = {key: value for key, value in os.environ.items() if key.upper() in {
        'PATH', 'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'PROCESSOR_ARCHITECTURE',
        'NUMBER_OF_PROCESSORS', 'LANG', 'LC_ALL'}}
    env.update({
        'PATH': str(node.parent) + os.pathsep + env.get('PATH', ''),
        'OPENCODE_CONFIG': str(root / 'opencode.json'), 'OPENCODE_CONFIG_DIR': str(root / 'config'),
        'OPENCODE_TEST_HOME': str(root / 'home'), 'HOME': str(root / 'home'), 'USERPROFILE': str(root / 'home'),
        'TEMP': str(root / 'temp'), 'TMP': str(root / 'temp'), 'OPENCODE_DISABLE_AUTOUPDATE': 'true',
        'OPENCODE_DISABLE_MODELS_FETCH': 'true', 'OPENCODE_DISABLE_PROJECT_CONFIG': 'true', 'OPENCODE_PURE': 'true',
        'OPENCODE_DISABLE_DEFAULT_PLUGINS': 'true', 'OPENCODE_DISABLE_EXTERNAL_SKILLS': 'true',
        'OPENCODE_DISABLE_CLAUDE_CODE': 'true', 'OPENCODE_DISABLE_LSP_DOWNLOAD': 'true',
        'OPENCODE_EXPERIMENTAL_NATIVE_LLM': 'false', 'OPENCODE_EXPERIMENTAL': 'false',
        'XDG_DATA_HOME': str(root / 'data'), 'XDG_CONFIG_HOME': str(root / 'config'),
        'XDG_CACHE_HOME': str(root / 'cache'), 'XDG_STATE_HOME': str(root / 'state'), 'NO_COLOR': '1',
        'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': str(root / 'home' / 'empty-gitconfig'),
        'LAB_CONTROL_DIR': str(root / 'control'), 'LAB_RUN_NONCE': nonce, 'LAB_GENERATOR_TIMEOUT_MS': '180000',
    })
    (root / 'home' / 'empty-gitconfig').write_text('', encoding='utf-8')
    write_json(root / 'environment.json', env)
    write_json(root / 'profile-identity.json', {'nonce': nonce, 'workspace': str(workspace),
        'data': str(root / 'data'), 'config': str(root / 'opencode.json')})
    overall_deadline = time.monotonic() + 600
    recorder = Recorder(root, workspace, env, deadline=overall_deadline)
    provider = ScriptedProvider(recorder)
    config = {'model': 'lab/scripted', 'small_model': 'lab/scripted', 'default_agent': 'builder',
        'enabled_providers': ['lab'], 'share': 'disabled', 'autoupdate': False, 'username': 'lab',
        'snapshot': True, 'lsp': False, 'formatter': False, 'shell': str(shell),
        'permission': {'*': 'deny'}, 'agent': roles(),
        'provider': {'lab': {'npm': '@ai-sdk/openai-compatible', 'name': 'Scripted fixture',
            'options': {'baseURL': provider.url, 'apiKey': 'lab'},
            'models': {'scripted': {'name': 'No inference', 'limit': {'context': 32768, 'output': 4096}}}}}}
    write_json(root / 'opencode.json', config)
    owned, extra_handles = [], []
    monitor = None
    sid = None
    server = None
    generator = shell_process = None

    def check_deadline():
        if time.monotonic() > overall_deadline:
            raise TimeoutError('Overall case deadline exceeded')

    def launch(command, stem, image):
        check_deadline()
        out = (root / (stem + '.stdout')).open('wb')
        err = (root / (stem + '.stderr')).open('wb')
        start = recorder.event('process_launch', stem=stem)
        try:
            child = subprocess.Popen(command, cwd=workspace, env=env, stdout=out, stderr=err,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
        except BaseException:
            out.close()
            err.close()
            raise
        record = {'process': child, 'observer': None, 'out': out, 'err': err, 'stem': stem}
        owned.append(record)
        observer = Process.from_popen(child, image)
        record['observer'] = observer
        write_json(root / (stem + '.launch.json'), {
            'command': [str(value) for value in command], 'cwd': str(workspace),
            'start_ns': start['time_ns'], 'identity': observer.observe(),
            'profile_sha256': sha((root / 'profile-identity.json').read_bytes()),
            'config_sha256': sha((root / 'opencode.json').read_bytes()),
            'environment_sha256': sha((root / 'environment.json').read_bytes())})
        return record

    def terminate(record, cause):
        recorder.event('harness_process_termination_start', stem=record['stem'], cause=cause)
        if record['observer'] is None:
            # Popen itself owns this exact child even if observer construction failed.
            record['process'].kill()
            record['process'].wait(timeout=10)
            result = {'observer_unavailable': True, 'returncode': record['process'].returncode}
        else:
            result = record['observer'].terminate()
            record['process'].wait(timeout=10)
        write_json(root / (record['stem'] + '-' + cause + '.termination.json'), result)
        recorder.event('harness_process_termination_return', stem=record['stem'], cause=cause)

    def start_server(stem):
        record = launch([str(cli), '--print-logs', '--log-level', 'INFO', 'serve', '--pure',
                         '--hostname', '127.0.0.1', '--port', '0'], stem, cli)
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            value = (root / (stem + '.stdout')).read_text(encoding='utf-8', errors='replace')
            match = re.search(r'http://127\.0\.0\.1:\d+', value)
            if match:
                recorder.url = match.group(0)
                recorder.event('server_ready', stem=stem, url=recorder.url)
                return record
            if record['process'].poll() is not None:
                raise RuntimeError('Server exited during startup')
            time.sleep(.05)
        raise TimeoutError('Server startup deadline exceeded')

    def mark(name):
        recorder.event('control_marker_start', name=name)
        write_json(root / 'control' / name, {'nonce': nonce})
        recorder.event('control_marker_return', name=name)

    def processes(stem):
        start = recorder.event('process_observation_start', stem=stem)
        result = {name: process.observe() for name, process in {
            'server': server['observer'], 'shell': shell_process, 'generator': generator}.items() if process}
        end = recorder.event('process_observation_return', stem=stem)
        write_json(root / (stem + '.processes.json'), {
            'start_ns': start['time_ns'], 'end_ns': end['time_ns'], 'processes': result})
        return result

    def state(stage, remote=True):
        check_deadline()
        start = recorder.event('state_start', stage=stage)
        info, messages = {}, []
        if remote:
            recorder.api('GET', '/session/status', stage + '-status')
            info = recorder.api('GET', '/session/' + sid, stage + '-session')
            messages = recorder.api('GET', '/session/' + sid + '/message', stage + '-messages')
            recorder.snapshots(info, messages, stage)
        before = recorder.files(stage + '-before-test')
        recorder.command([str(node), '--test', '--test-reporter=tap', 'acceptance.test.mjs'], stage + '-acceptance')
        after = recorder.files(stage + '-after-test')
        if before['files'] != after['files']:
            raise RuntimeError('Files changed during the independent acceptance check')
        end = recorder.event('state_return', stage=stage, provider_requests=provider.count)
        write_json(root / (stage + '.state.json'), {'start_ns': start['time_ns'], 'end_ns': end['time_ns'],
            'remote': remote, 'provider_requests': provider.count, 'session': sid})
        return info, messages, before

    def settle_client(record, timeout=30):
        start = recorder.event('client_wait_start', stem=record['stem'])
        timed_out = False
        try:
            record['process'].wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        end = recorder.event('client_wait_return', stem=record['stem'], timed_out=timed_out,
                             exit=record['process'].returncode)
        write_json(root / (record['stem'] + '.settlement.json'), {
            'start_ns': start['time_ns'], 'end_ns': end['time_ns'], 'timed_out': timed_out,
            'returncode': record['process'].returncode, 'process': record['observer'].observe()})
        return not timed_out

    def cleanup_generator(cause):
        current = processes(cause + '-before-cleanup')
        if any(current.get(name, {}).get('alive') for name in ('generator', 'shell')):
            mark('stop.json')
            if generator:
                generator.observe(10000)
            if shell_process:
                shell_process.observe(10000)
            for name, process in (('generator', generator), ('shell', shell_process)):
                if process and process.observe()['alive']:
                    recorder.event('harness_child_termination_start', role=name, cause=cause)
                    write_json(root / (cause + '-' + name + '.termination.json'), process.terminate())
                    recorder.event('harness_child_termination_return', role=name, cause=cause)
        processes(cause + '-after-cleanup')

    try:
        setup = [['git', '-c', 'init.templateDir=', 'init', '--quiet'], ['git', 'add', '--', *FILES],
            ['git', '-c', 'core.hooksPath=' + str(root / 'hooks'), '-c', 'commit.gpgsign=false',
             '-c', 'user.name=Synthetic Lab', '-c', 'user.email=lab@example.invalid',
             'commit', '--quiet', '-m', 'Synthetic fixture'], ['git', 'rev-parse', '--show-toplevel'],
            ['git', 'status', '--porcelain']]
        for index, command in enumerate(setup):
            recorder.command(command, f'git-setup-{index}').check_returncode()
        for stem, command in [('version', [str(cli), '--version']), ('node-version', [str(node), '--version']),
            ('shell-version', [str(shell), '-NoProfile', '-Command', '$PSVersionTable.PSVersion.ToString()']),
            ('git-version', ['git', '--version']), ('resolved-config', [str(cli), 'debug', 'config', '--pure']),
            ('resolved-agent', [str(cli), 'debug', 'agent', 'builder', '--pure'])]:
            recorder.command(command, stem, timeout=45).check_returncode()
        server = start_server('server-1')
        created = recorder.api('POST', '/session', 'create-session', {'title': 'Synthetic interrupted catalogue',
            'agent': 'builder', 'model': {'providerID': 'lab', 'id': 'scripted'}})
        sid = provider.session = created['id']
        write_json(root / 'identity.json', {'case': case, 'nonce': nonce, 'session': sid,
                                           'workspace': str(workspace), 'source_commit': PIN})
        state('initial')
        client = launch([str(cli), 'run', '--pure', '--attach', recorder.url, '--session', sid,
            '--format', 'json', '--model', 'lab/scripted', '--agent', 'builder', '--', PROMPT], 'client', cli)
        deadline = time.monotonic() + 45
        ready_path = root / 'control' / 'ready.json'
        while not ready_path.exists():
            if time.monotonic() >= deadline or client['process'].poll() is not None:
                raise RuntimeError('Unfinished generator barrier was not reached')
            time.sleep(.05)
        ready = json.loads(ready_path.read_text(encoding='utf-8'))
        if ready.get('nonce') != nonce or ready.get('stage') != 'catalogue-written':
            raise RuntimeError('Unexpected generator coordination identity')
        shell_process, generator, ancestry = bind_generator(ready['pid'], server['observer'], node, shell)
        extra_handles.extend([shell_process, generator])
        write_json(root / 'barrier-ancestry.json', ancestry)
        monitor = Monitor(recorder, {'server': server['observer'], 'shell': shell_process, 'generator': generator})
        info, messages, files = state('barrier')
        users = [message for message in messages if message['info']['role'] == 'user']
        target_parts = [part for message in messages for part in message['parts']
                        if part['type'] == 'tool' and part.get('callID') == CALLS[-1][0]]
        edit_parts = [part for message in messages for part in message['parts']
                      if part['type'] == 'tool' and part.get('callID') == 'edit_labels']
        if len(users) != 1 or len(target_parts) != 1 or target_parts[0]['state']['status'] != 'running':
            raise RuntimeError('Barrier lacks the expected user and running generator tool')
        if len(edit_parts) != 1 or edit_parts[0]['state']['status'] != 'completed':
            raise RuntimeError('The earlier built-in edit is not recorded as completed')
        expected = intended_files()
        expected['catalogue.manifest.json'] = fixture('catalogue.manifest.json')
        actual = {name: base64.b64decode(value['base64']) for name, value in files['files'].items()}
        if actual != expected:
            raise RuntimeError('Independent barrier file witness differs from the intended partial state')
        if not any(base64.b64decode(tree['files'].get('catalogue.json', {}).get('base64', ''))
                   == fixture('catalogue.json') for tree in recorder.trees.values()):
            raise RuntimeError('No pre-intervention saved catalogue bytes; inspect snapshot errors and path length')
        if not generator.observe()['alive'] or (root / 'control' / 'release.json').exists():
            raise RuntimeError('Generator no longer held at the live barrier')
        target = users[0]['info']['id']
        write_json(root / 'barrier-admission.json', {'user_message': target, 'tool_part': target_parts[0]['id'],
            'tool_call': target_parts[0]['callID'], 'files_end_ns': files['end_ns'],
            'process': generator.observe(), 'release_present': False})
        recorder.event('barrier_admitted', target=target, tool_part=target_parts[0]['id'])

        if case == 'normal':
            mark('release.json')
        elif case == 'graceful':
            if recorder.api('POST', '/session/' + sid + '/abort', 'abort', {}) is not True:
                raise RuntimeError('Unexpected abort response')
        else:
            selected = {Path(name).name for message in messages for part in message['parts']
                        if part['type'] == 'patch' for name in part['files']}
            if 'catalogue.json' in selected:
                raise RuntimeError('Forced-stop coverage contrast is already absent at the barrier')
            if not any(base64.b64decode(tree['files'].get('catalogue.json', {}).get('base64', ''))
                       == fixture('catalogue.json') for tree in recorder.trees.values()):
                raise RuntimeError('No pre-intervention saved catalogue version was witnessed')
            terminate(server, 'active-server-stop')
        processes('immediate-post-intervention')
        recorder.files('immediate-post-intervention')
        if case == 'forced':
            # Fixed natural-observation window before any harness child cleanup.
            generator.observe(1000)
            state('primary', remote=False)
            monitor.close()
            monitor = None
            cleanup_generator('forced')
            if not settle_client(client, 10):
                terminate(client, 'disconnected-client-cleanup')
        else:
            generator.observe(10000)
            settled = settle_client(client)
            state('primary')
            processes('primary')
            monitor.close()
            monitor = None
            cleanup_generator('primary')
            if not settled:
                terminate(client, 'client-timeout-cleanup')
            state('reopened')
            terminate(server, 'quiescent-restart')
        recorder.files('quiescent-before-restart')
        recorder.event('restart_begin')
        server = start_server('server-2')
        info, messages, _ = state('restarted')
        if info.get('revert'):
            raise RuntimeError('Expected first revert without an existing marker')
        recorder.api('POST', '/session/' + sid + '/revert', 'first-revert', {'messageID': target})
        state('reverted')
        recorder.api('POST', '/session/' + sid + '/unrevert', 'unrevert', {})
        state('unreverted')
        if provider.errors:
            raise RuntimeError('Provider errors occurred; evidence retained')
        recorder.event('case_capture_complete', case=case)
        print(case + ': captures retained; independent verification is still required.', flush=True)
    except BaseException as error:
        write_json(root / 'collection-error.json', {'error': repr(error), 'traceback': traceback.format_exc()})
        recorder.event('collection_error', error=repr(error))
        raise
    finally:
        cleanup_errors = []
        if monitor:
            try:
                monitor.close()
            except Exception as error:
                cleanup_errors.append(repr(error))
        # A marker can stop only this fixture helper, including before identity
        # acquisition. Never kill an unverified PID from a readiness descriptor.
        try:
            mark('stop.json')
            if generator:
                generator.observe(3000)
            for process in (generator, shell_process):
                if process and process.observe()['alive']:
                    recorder.event('emergency_child_cleanup', pid=process.pid)
                    process.terminate()
        except Exception as error:
            cleanup_errors.append(repr(error))
        for record in reversed(owned):
            try:
                if record['process'].poll() is None:
                    terminate(record, 'final-cleanup')
            except Exception as error:
                cleanup_errors.append(repr(error))
            finally:
                if record['observer']:
                    record['observer'].close()
                record['out'].close()
                record['err'].close()
        for handle in extra_handles:
            handle.close()
        try:
            provider.close()
        except Exception as error:
            cleanup_errors.append(repr(error))
        write_json(root / 'cleanup.json', {'errors': cleanup_errors})
        if cleanup_errors:
            raise RuntimeError('Cleanup errors retained in cleanup.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', required=True, type=Path)
    parser.add_argument('--node', type=Path, default=shutil.which('node'))
    parser.add_argument('--shell', type=Path, default=shutil.which('pwsh'))
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--include-forced-stop', action='store_true',
                        help='Add the separately justified active-server-stop case after a validated pilot pair')
    args = parser.parse_args()
    if platform.system() != 'Windows' or not args.node or not args.shell:
        parser.error('Live collection requires Windows, Node and PowerShell 7; offline checks are portable')
    cli, node, shell = args.opencode.resolve(), args.node.resolve(), args.shell.resolve()
    if sha(cli.read_bytes()) != BINARY_SHA256:
        parser.error('Expected the official v1.18.30 Windows x64 binary digest')
    checkout = LAB.parents[4]
    if args.output.resolve().is_relative_to(checkout):
        parser.error('Private captures must be outside this checkout')
    longest_gitdir = args.output.resolve() / 'interruption-xxxxxxxx' / 'graceful' / 'data' / 'opencode' / 'snapshot' / ('a' * 40) / ('b' * 40)
    if len(str(longest_gitdir).encode('utf-8')) > 230:
        parser.error('Use a shorter private output root; the generated Windows Git snapshot directory would be too long')
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix='interruption-', dir=args.output.resolve()))
    print('Private capture: ' + str(root), flush=True)
    metadata = {'schema': 1, 'run_id': root.name, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'source_commit': PIN, 'binary_sha256': sha(cli.read_bytes()), 'platform': platform.platform(),
        'python': sys.version, 'cases': list(CASES if args.include_forced_stop else CASES[:2]),
        'files': {str(path.relative_to(LAB)).replace('\\', '/'): sha(path.read_bytes())
                  for folder in ('scripts', 'fixtures') for path in sorted((LAB / folder).rglob('*'))
                  if path.is_file() and '__pycache__' not in path.parts}}
    write_json(root / 'run.json', metadata)
    for name, digest in metadata['files'].items():
        data = (LAB / name).read_bytes()
        if sha(data) != digest:
            raise RuntimeError('Lab source changed during capture initialization')
        destination = root / 'implementation' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    provenance = Recorder(root, checkout, os.environ.copy())
    provenance.command(['git', 'rev-parse', 'HEAD'], 'lab-revision').check_returncode()
    provenance.command(['git', 'status', '--porcelain', '--untracked-files=all', '--', str(LAB)],
                       'lab-status').check_returncode()
    for case in metadata['cases']:
        run_case(root / case, case, cli, node, shell)
    print('Collection finished. Run verify_run.py on this private capture.', flush=True)


if __name__ == '__main__':
    main()
