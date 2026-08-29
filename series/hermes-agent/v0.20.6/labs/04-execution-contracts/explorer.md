# Explorer track

## Goal

Run the execution contract without Hermes, inspect its evidence, and learn why “the agent said it worked” is not a completion criterion.

## 1. Create a disposable workspace

Use the initializer from the [lab README](README.md). Change into the printed directory.

## 2. Run the control matrix

From the repository root, use the PowerShell or Bash command shown in the README. The runner prints one JSON result with seven boolean checks.

The important files inside the disposable workspace are:

~~~text
evidence/
├── attempts/
│   ├── control-success-dry.json
│   ├── control-success-apply.json
│   └── control-success-duplicate.json
└── operations/
    └── control-success.json
~~~

The attempt receipts tell you what happened on each try. The operation record points to the first committed attempt.

## 3. Verify without trusting prose

macOS or Linux:

~~~bash
python3 ./bin/verify_operation.py \
  --workspace . \
  --operation-id control-success \
  --execution-mode script
~~~

Windows:

~~~powershell
python ./bin/verify_operation.py `
  --workspace . `
  --operation-id control-success `
  --execution-mode script
~~~

The verifier independently checks status, mode, policy, procedure, output existence, and output hash.

## 4. Read the duplicate evidence

Compare `control-success-apply.json` with `control-success-duplicate.json`.

- The first says `status: committed` and `mutation: applied`.
- The second says `status: duplicate` and `mutation: suppressed`.
- The committed operation still names the first apply attempt as `primary_attempt_id`.

## Modification challenge

Create a new disposable workspace. Render a direct operation with:

~~~bash
python3 ./bin/render_commands.py --workspace . --execution-mode direct --operation-id explorer-change
~~~

Before executing it, replace `HERMES-P4-PROCEDURE-V2` in the dry-run command with `HERMES-P4-PROCEDURE-V1`. Predict which evidence file will be created and whether the deployed artifact will exist.

Expected result: the attempt is recorded as rejected, and no artifact or committed-operation record is created.
