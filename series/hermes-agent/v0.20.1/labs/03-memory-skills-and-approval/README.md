# Lab 03: Durable memory, reusable skills, and approval gates

## Central question

What changes when Hermes remembers a fact, stores a preference, or commits a reusable procedure—and when does each change become active?

## What you will learn

By the end of this lab, you should be able to distinguish:

- conversation history from durable memory
- environment facts in `MEMORY.md` from user preferences in `USER.md`
- a skill's compact routing description from its full `SKILL.md` body
- a staged proposal from an approved durable write
- durable commit from activation in a fresh model request
- an agent's claim of success from filesystem, provider-boundary, and execution receipts

## The shortest useful model

| Durable knowledge | Best home | What the model initially sees |
| --- | --- | --- |
| Stable environment fact | `MEMORY.md` | The fact in durable prompt context |
| Stable user preference | `USER.md` | The preference in user-profile context |
| Reusable multi-step procedure | `skills/<name>/SKILL.md` | A compact skill index entry; the body is loaded on demand |

With write approval enabled, a model-requested mutation first becomes a pending JSON record. Rejection removes that proposal without changing the durable target. Approval applies the proposal, but the cleanest activation checkpoint is a fresh session and provider request.

## Synthetic markers

| Marker | Intended path |
| --- | --- |
| `HERMES-P3-FACT-EU-WEST-2` | Approved environment fact |
| `HERMES-P3-PREF-DRY-RUN-FIRST` | Approved user preference |
| `HERMES-P3-REJECTED-CANARY` | Rejected memory proposal |
| `HERMES-P3-INCOMPLETE-SKILL-CANARY` | Rejected skill proposal |
| `HERMES-P3-SKILL-LOCAL-DEPLOY-V1` | Approved and loaded procedure |

## Choose a track

- [Explorer](explorer.md): run the network-free deployment fixture and inspect sanitized evidence. No provider account is needed.
- [Builder](builder.md): reproduce staging, rejection, approval, and fresh-session reuse with your own isolated Hermes profile.
- [Investigator](investigator.md): capture provider-boundary marker receipts, add controls, and submit a compatibility result.

## Reference finding

On Windows, with Hermes v0.20.1 pinned to tag `v2026.8.13` and commit `f80f453ae0679347e38abc917c7f94f717bf96c5`, the successful provider-backed pass produced:

- 18 of 18 lifecycle and execution checks passing
- 32 provider requests across seven agent turns
- 13 completed tool calls
- approved fact and preference markers in a fresh provider-bound system prompt
- an approved skill index marker in that prompt, followed by a `skill_view` load
- neither rejected canary in the fresh-session response
- a dry-run receipt before the real local deployment
- a verified, network-free artifact with SHA-256 `93a8282a18351bb4c3c95d6f584808c32bbf3dea0370fb930ac668dc7b9ff58b`

The first attempt was also informative: Hermes refused the otherwise complete skill at approval because its routing description was 152 characters, beyond the 60-character budget enforced at this pin. The accepted replacement used a 54-character description and kept the detail in the body.

See [the sanitized reference result](reference-results/windows-2026-08-23/README.md) and [claim matrix](expected/claim-matrix.md).

## Start here

macOS or Linux:

~~~bash
bash ./scripts/initialize-lab.sh
bash ./scripts/test-lab-fixtures.sh
~~~

Windows with PowerShell 7:

~~~powershell
pwsh ./scripts/Initialize-Lab.ps1
pwsh ./scripts/Test-LabFixtures.ps1
~~~

The initializer prints a unique disposable lab path. The fixture scripts use only that directory, make no network calls, and require a matching dry-run receipt before local deployment.

## Cost and safety

The Explorer track is free and network-free. Builder and Investigator runs may consume provider tokens.

Never point `HERMES_HOME` at your normal profile for this lab. Do not publish `auth.json`, `.env`, session databases, raw provider request bodies, system prompts, or absolute home-directory paths.
