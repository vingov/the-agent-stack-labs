"""Fixed synthetic inputs and acceptance contract, independent of provider assertions."""
import hashlib
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
PIN = '3104c1428ec91f809e5ab86631300de41eb6952e'
BINARY_SHA256 = 'c1bdbb18767048e1853af4238311b3f7e16ff2f91b68fb4c7ced3c5175347eea'
MARKERS = {'parent': 'PARENT_ONLY_4a86d1', 'delegated': 'HANDOFF_9e31f6', 'observation': 'CHILD_READ_7b52c9'}
TASK = {'description': 'Trim label whitespace', 'subagent_type': 'general',
        'prompt': 'Read labels.mjs and labels.test.mjs. Trim outer whitespace and preserve interior spaces. '
                  'Edit only labels.mjs. Report the change for the parent to check. Handoff marker: ' + MARKERS['delegated']}
PROMPT = ('Delegate the bounded label edit to general, then run the fixed tests. '
          'This note belongs only to the parent conversation: ' + MARKERS['parent'])
EDIT = {'filePath': 'labels.mjs', 'oldString': 'return label;', 'newString': 'return label.trim();'}
CHECK = {'command': 'node --test labels.test.mjs', 'description': 'Check label behavior'}
SUMMARY = 'Changed labels.mjs to trim outer whitespace while preserving interior spaces. Parent must run the fixed tests.'
FILES = ['labels.mjs', 'labels.test.mjs']
ROOT_RULES = [{'permission': p, 'pattern': '*', 'action': 'deny'} for p in ['question', 'plan_enter', 'plan_exit']]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def fixture(name):
    return (LAB / 'fixtures' / name).read_text(encoding='utf-8').encode()

def expected_files(changed=False):
    result = {name: fixture(name) for name in FILES}
    if changed:
        result['labels.mjs'] = result['labels.mjs'].replace(EDIT['oldString'].encode(), EDIT['newString'].encode())
    return result

def marker_presence(value):
    import json
    text = json.dumps(value, ensure_ascii=False)
    return {name: marker in text for name, marker in MARKERS.items()}

def policy():
    return {'build': {'mode': 'primary', 'permission': {
                'task': {'*': 'deny', 'general': 'allow'},
                'bash': {'*': 'deny', CHECK['command']: 'allow'}}},
            'general': {'mode': 'subagent', 'permission': {
                'read': {'*': 'deny', 'labels.mjs': 'allow', 'labels.test.mjs': 'allow'},
                'edit': {'*': 'deny', 'labels.mjs': 'allow'}}}}
