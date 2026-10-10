"""Inputs for moving one restriction across a fresh delegation boundary."""
from contract import BINARY_SHA256, EDIT, FILES, LAB, MARKERS, PIN, ROOT_RULES, fixture, sha

CASES = ('allowed', 'parent-role-direct', 'parent-role', 'parent-session', 'worker-role', 'dispatch')
CHANGED = {'allowed', 'parent-role'}
TASK = {'description': 'Bounded label edit', 'subagent_type': 'worker',
        'prompt': 'Read labels.mjs and labels.test.mjs. Edit only labels.mjs to trim outer whitespace '
                  'and preserve interior spaces. Report the operation result. Handoff marker: ' + MARKERS['delegated']}
PROMPT = ('Delegate the bounded label edit to worker. Parent-only note: ' + MARKERS['parent'])
DIRECT_PROMPT = ('Read labels.mjs and labels.test.mjs, then apply the bounded trim edit directly. '
                 'Parent-only note: ' + MARKERS['parent'])
SUCCESS = 'The edit tool completed the requested label change. Fixed tests still need independent checking.'
DENIED = 'The requested edit was denied by the runtime. No edit was completed.'
PARENT_FINAL = 'The scripted parent received the tool result. Independent file and test checks follow.'

def roles(case):
    read = {'*': 'deny', 'labels.mjs': 'allow', 'labels.test.mjs': 'allow'}
    def edit(action):
        # A specific last rule leaves the tool exposed, so each case reaches its gate.
        return {'*': 'deny', 'labels.mjs': action}
    return {
        'coordinator': {'mode': 'primary', 'description': 'Synthetic delegation coordinator',
            'permission': {'read': read, 'edit': edit('deny' if case in ('parent-role-direct', 'parent-role') else 'allow'),
                           'task': {'*': 'deny', 'worker': 'deny' if case == 'dispatch' else 'allow'}}},
        'worker': {'mode': 'subagent', 'description': 'Synthetic bounded label worker',
            'permission': {'read': read, 'edit': edit('deny' if case == 'worker-role' else 'allow')}}}

def session_rules(case):
    return ROOT_RULES + ([{'permission': 'edit', 'pattern': 'labels.mjs', 'action': 'deny'}]
                         if case == 'parent-session' else [])

def calls(case):
    if case == 'dispatch':
        return [('parent_task', 'task', TASK)]
    owner = 'parent' if case == 'parent-role-direct' else 'child'
    operations = [(owner + '_read_helper', 'read', {'filePath': 'labels.mjs'}),
                  (owner + '_read_tests', 'read', {'filePath': 'labels.test.mjs'}),
                  (owner + '_edit', 'edit', EDIT)]
    return operations if owner == 'parent' else [('parent_task', 'task', TASK), *operations]
