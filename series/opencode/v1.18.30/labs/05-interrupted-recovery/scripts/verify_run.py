"""Reconstruct a private live capture and optionally export its sanitized receipt."""
import argparse
import json
from pathlib import Path
from evidence import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--implementation', type=Path, help='Explicit archived source for older development pilots only')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.capture, args.implementation)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    for case in result['cases']:
        print(case['case'], 'validated;', 'unselected changed paths:', case['unselected_changed_paths'],
              '; baseline restored:', case['restored_baseline'])


if __name__ == '__main__':
    main()
