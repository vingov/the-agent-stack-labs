"""Fixed synthetic task and inputs. Runtime outcomes are collected separately."""
import hashlib
import json
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PIN = '3104c1428ec91f809e5ab86631300de41eb6952e'
BINARY_SHA256 = 'c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea'
CASES = ('normal', 'graceful', 'forced')
FILES = ('.gitattributes', 'labels.mjs', 'source-data.json', 'generate-catalogue.mjs',
         'catalogue.json', 'catalogue.manifest.json', 'acceptance.test.mjs')
IMMUTABLE = ('.gitattributes', 'source-data.json', 'generate-catalogue.mjs', 'acceptance.test.mjs')
COMMAND = 'node ./generate-catalogue.mjs'
EDIT = {'filePath': 'labels.mjs', 'oldString': 'return label;', 'newString': 'return label.trim();'}
CALLS = [
    ('read_labels', 'read', {'filePath': 'labels.mjs'}),
    ('read_acceptance', 'read', {'filePath': 'acceptance.test.mjs'}),
    ('read_generator', 'read', {'filePath': 'generate-catalogue.mjs'}),
    ('read_input', 'read', {'filePath': 'source-data.json'}),
    ('edit_labels', 'edit', EDIT),
    ('generate_catalogue', 'bash', {'command': COMMAND, 'timeout': 120000}),
]
PROMPT = ('Read labels.mjs, acceptance.test.mjs, generate-catalogue.mjs and source-data.json. '
          'Change only normalizeLabel in labels.mjs to trim outer whitespace while preserving interior spaces. '
          'Then run node ./generate-catalogue.mjs to regenerate the catalogue and matching manifest. '
          'Do not edit the generator, input, or tests. Task marker: INTERRUPTED_CATALOGUE_V1.')
FINAL = 'The prescribed edit and generation operations returned. Independent acceptance follows.'
TEST_NAMES = (
    'preserves meaningful interior spaces', 'trims outer whitespace',
    'normalizes an all-whitespace label', 'preserves the empty label',
    'catalogue has the intended label values', 'manifest identifies the actual catalogue bytes',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(name):
    if name not in FILES:
        raise ValueError('Unknown fixture path')
    return (LAB / 'fixtures' / name).read_bytes()


def intended_files():
    result = {name: fixture(name) for name in FILES}
    result['labels.mjs'] = result['labels.mjs'].replace(b'return label;', b'return label.trim();')
    catalogue = (json.dumps({'labels': ['Alpha', 'Beta  Gamma', 'Delta']}, indent=2) + '\n').encode()
    result['catalogue.json'] = catalogue
    result['catalogue.manifest.json'] = (json.dumps({
        'algorithm': 'sha256', 'catalogueSha256': sha(catalogue)}, indent=2) + '\n').encode()
    return result


def roles():
    reads = {args['filePath']: 'allow' for _, tool, args in CALLS if tool == 'read'}
    return {'builder': {'mode': 'primary', 'description': 'Synthetic interrupted catalogue task',
            'permission': {'read': {'*': 'deny', **reads},
                           'edit': {'*': 'deny', 'labels.mjs': 'allow'},
                           'bash': {'*': 'deny', COMMAND: 'allow'}}}}
