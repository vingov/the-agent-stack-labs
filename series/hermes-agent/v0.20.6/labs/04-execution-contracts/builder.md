# Builder track

## Goal

Give the same bounded operation to a normal Hermes session and a delegated child, then compare who owned the tool calls and what evidence remained.

## Prerequisites

- Hermes Agent v0.20.6
- a configured provider for live runs
- a disposable `HERMES_HOME`
- two newly initialized workspaces, one for direct execution and one for delegation

The operation scripts are network-free. Hermes provider calls are not.

## 1. Render exact commands

In the direct workspace:

~~~bash
python ./bin/render_commands.py \
  --workspace . \
  --execution-mode direct \
  --operation-id builder-direct-v2
~~~

On Windows, the same command works in PowerShell without the Bash line continuations. The result is JSON containing `dry_run`, `apply`, and `verify` commands. Keep the commands as separate delimiter-bounded lines; do not add sentence punctuation.

## 2. Run directly

Start Hermes in the direct workspace with only the terminal toolset enabled. Give it this prompt, replacing the two placeholders with the rendered commands:

~~~text
Execute exactly two terminal commands in order. Do not include marker lines,
surrounding text, or punctuation in either command.
BEGIN DRY COMMAND
<dry_run>
END DRY COMMAND
BEGIN APPLY COMMAND
<apply>
END APPLY COMMAND
Report the two statuses and output SHA-256. Do not use terminal network commands
or modify paths outside this workspace.
~~~

After Hermes responds, run the rendered `verify` command yourself. Treat the verifier as evidence and the prose response as a claim.

## 3. Run through one leaf child

Initialize a second workspace and render commands with `--execution-mode delegated --operation-id builder-delegated-v2`.

Start the parent with the `delegation` and `terminal` toolsets. Ask it to call `delegate_task` exactly once, put both delimiter-bounded commands in the child's explicit context, and leave execution to the child. The parent should report the child result without rerunning the commands itself.

Check three boundaries:

1. the parent trace contains a delegation call, not direct terminal execution;
2. the child trace contains the dry run, apply, and optional verify calls; and
3. the committed-operation record says `execution_mode: delegated`.

The child starts with fresh conversation context. Any required path, policy, command, or success criterion must be in its `goal` or `context`; “do what we discussed” is an invalid delegation contract.

## 4. Narrow the capability

Create a third workspace. Start the parent with `delegation` but without `terminal`, then repeat the task.

Expected result at the reference pin: the leaf inherits the narrowed toolset, makes zero terminal calls, and creates no receipt. This is the control that distinguishes actual inherited authority from a model merely describing delegation.

## Troubleshooting

- If an operation says `duplicate`, you reused a logical operation in the same workspace. Initialize a new workspace or choose a new operation ID.
- If an attempt says it already exists, choose a new attempt ID; never delete a receipt to make a retry look like the first attempt.
- If a command reports an unknown argument `.` or another punctuation mark, rebuild the prompt with explicit markers.
- If the child cannot locate a file, put the absolute workspace and commands in the delegation context.
