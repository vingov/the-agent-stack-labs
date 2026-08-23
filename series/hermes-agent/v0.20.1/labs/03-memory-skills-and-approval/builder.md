# Builder track

## Goal

Use the supported Hermes CLI with a disposable profile to reproduce the memory and skill lifecycle.

## Prerequisites

- Hermes Agent v0.20.1
- a provider configured inside the disposable profile
- PowerShell 7 on Windows, or Bash plus Python 3 on macOS/Linux
- the initialized lab from the [README](README.md)

## 1. Verify isolation

Set `HERMES_HOME` to the initializer's printed `profile` path and change into `workspace/hermes-part3-lab`. Confirm the path before authenticating or starting Hermes. The included config enables both write-approval gates.

## 2. Propose a fact

Ask Hermes:

> Remember the stable environment fact `HERMES-P3-FACT-EU-WEST-2: the synthetic staging region is eu-west-2` in durable memory.

Checkpoint: Hermes should say the change is staged, not saved. Review it with `/memory pending`, then approve its ID. Confirm the marker appears under the disposable profile's `memories/MEMORY.md`.

## 3. Propose a preference

Ask Hermes:

> Remember the stable user preference `HERMES-P3-PREF-DRY-RUN-FIRST: before any deployment, run and inspect a dry run first` in the user profile.

Review and approve it. Confirm the marker follows the `memories/USER.md` path rather than `MEMORY.md`.

## 4. Exercise rejection

Stage `HERMES-P3-REJECTED-CANARY: deliberately reject this candidate` as memory. Hash the durable files, reject the proposal, and hash them again. The durable hashes should not change.

## 5. Create the procedure

Give Hermes the exact file at [expected/local-deploy/SKILL.md](expected/local-deploy/SKILL.md) and ask it to create a skill named `local-deploy`. Review `/skills diff <id>` before approval.

Checkpoint: the short description is 54 characters. At this pin, a description longer than 60 characters is rejected during approval even when the body is valid.

## 6. Verify activation and reuse

Start a fresh Hermes session and ask it to deploy the synthetic fixture with run ID `P3-BUILD-0001`, using durable context and the applicable skill. Do not paste the procedure again.

The strong checkpoint is not the final prose response. Capture evidence that:

1. the provider-bound system prompt contains the fact, preference, and skill-index markers;
2. Hermes calls `skill_view` for `local-deploy`;
3. the dry-run receipt exists before the deploy receipt;
4. verification reports the artifact digest; and
5. the rejected canaries are absent from fresh durable context.

## Recovery

If anything touches a non-disposable profile, stop. Preserve only sanitized hashes and receipts, remove the disposable run, create a new one, and start again.
