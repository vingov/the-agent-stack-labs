"""Reject tampered private evidence copies without rerunning OpenCode or changing the originals."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from verify_run import reconstruct
from verify_reference import EXPECTED, verify_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    source = args.run_directory.resolve()
    assert not verify_report(reconstruct(source)), 'Original raw capture must pass first'
    checked = 0
    with tempfile.TemporaryDirectory(prefix='opencode-permission-evidence-') as temporary:
        root = Path(temporary).resolve()
        # Cleanup is confined to this newly created test-only temporary directory.
        assert root.is_relative_to(Path(tempfile.gettempdir()).resolve())
        shutil.copy2(source / 'run.json', root / 'run.json')
        for name in EXPECTED:
            case = root / name
            case.mkdir()
            for path in (source / name).iterdir():
                if path.is_file():
                    shutil.copy2(path, case / path.name)
            for directory in ['before', 'after']:
                shutil.copytree(source / name / directory, case / directory)
            (case / 'workspace').mkdir()
            for path in (source / name / 'workspace').iterdir():
                if path.is_file():
                    shutil.copy2(path, case / 'workspace' / path.name)
        mutations = [
            ('missing actual evaluation', 'allow/cli.stderr.txt', lambda s: '\n'.join(
                line for line in s.splitlines() if not ('message=evaluated permission=edit' in line))),
            ('missing pending ask', 'ask_auto/cli.stderr.txt', lambda s: '\n'.join(
                line for line in s.splitlines() if 'message=asking' not in line)),
            ('hidden schema', 'deny_auto/request-02.json', lambda s: s.replace('"name": "edit"', '"name": "unavailable"')),
            ('different proposed arguments', 'allow/response-02.json', lambda s: s.replace('slug.mjs', 'different.mjs')),
            ('different runtime arguments', 'allow/export.stdout.txt', lambda s: s.replace('slug.mjs', 'different.mjs')),
            ('changed snapshot bytes', 'deny_auto/after/slug.mjs', lambda s: s + '// contradiction\n'),
            ('changed current bytes', 'ask/workspace/slug.mjs', lambda s: s + '// contradiction\n'),
            ('missing acceptance counters', 'allow/test-after.stdout.txt', lambda s: 'exit zero is not evidence\n'),
            ('missing formatter control', 'allow/cli.stderr.txt', lambda s: s.replace('all formatters are disabled', 'unknown')),
        ]
        for label, relative, change in mutations:
            path = root / relative
            original = path.read_bytes()
            modified = change(original.decode())
            assert modified != original.decode(), f'Control did not alter evidence: {label}'
            path.write_text(modified, encoding='utf-8')
            try:
                rejected = bool(verify_report(reconstruct(root)))
            except (OSError, ValueError, KeyError, TypeError):
                rejected = True
            finally:
                path.write_bytes(original)
            assert rejected, f'Accepted contradictory raw evidence: {label}'
            checked += 1
        assert not verify_report(reconstruct(root)), 'Restored copy must pass'
    print(f'PASS: {checked} raw-evidence rejection controls; original capture unchanged.')


if __name__ == '__main__':
    main()
