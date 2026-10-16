"""Synthetic inputs; restoration and acceptance have separate postconditions."""
import hashlib
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PIN = '3104c1428ec91f809e5ab86631300de41eb6952e'
BINARY_SHA256 = 'c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea'
CASES = ('control', 'same-file')
FILES = ('.gitattributes', 'labels.mjs', 'labels.test.mjs', 'notes.txt')
STAGES = ('r0', 'r1', 'r2', 'r3', 'r4')
PROMPT = ('Read labels.mjs and labels.test.mjs. Edit only the formatting function in labels.mjs '
          'to trim outer whitespace and preserve interior spaces. Leave displayMode unchanged. '
          'Original request marker: ORIGINAL_8f2c1a.')
CONTINUATION = 'Keep the current files. New branch marker: CONTINUE_51ac83.'
FINAL = 'The edit tool completed. Independent file and behavior checks follow.'
EDIT = {'filePath': 'labels.mjs', 'oldString': 'return label;', 'newString': 'return label.trim();'}
CALLS = [('read_helper', 'read', {'filePath': 'labels.mjs'}),
         ('read_tests', 'read', {'filePath': 'labels.test.mjs'}), ('edit_helper', 'edit', EDIT)]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def fixture(name):
    return (LAB / 'fixtures' / name).read_text(encoding='utf-8').encode()

def expected(case, stage):
    result = {n: fixture(n) for n in FILES}
    if stage in ('r1', 'r2', 'r4'):
        result['labels.mjs'] = result['labels.mjs'].replace(b'return label;', b'return label.trim();')
    if stage in ('r2', 'r3', 'r4', 'c0', 'c1'):
        result['notes.txt'] = b'Independent note: later work.\n'
    if case == 'same-file' and stage in ('r2', 'r4'):
        result['labels.mjs'] = result['labels.mjs'].replace(b"'compact'", b"'expanded'")
    return result

def roles():
    return {'builder': {'mode': 'primary', 'description': 'Synthetic bounded recovery task',
            'permission': {'read': {'*': 'deny', 'labels.mjs': 'allow', 'labels.test.mjs': 'allow'},
                           'edit': {'*': 'deny', 'labels.mjs': 'allow'}}}}
