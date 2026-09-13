# OpenCode: from a request to a verified patch

This lab replaces the model with a deterministic local provider while running the real OpenCode CLI. It isolates what the harness does with an answer, tool calls, and tool results.

Both cases end with the same scripted sentence: “The whitespace bug is fixed and the tests pass.” Both CLI processes exit successfully. Only the case that executes read, edit, and test tools changes the file and passes the independent verifier.

## What the result establishes

| Case | Real tool execution | File changed | Independent tests | CLI exit |
| --- | --- | --- | --- | --- |
| Answer only | None | No | Fail | 0 |
| Tool loop | read → edit → bash | Yes | Pass | 0 |

The harness can execute tool calls, return their results on subsequent provider requests, and finish a session. Its successful process exit does not certify the requested patch. The verifier checks the actual file after the run, using a test file whose hash is unchanged.

**Evidence class: OBSERVED_WITH_SCRIPTED_PROVIDER**, a qualified OBSERVED result. No language model made these decisions. The exact actions and final sentence were scripted by this fixture. This is neither a model-quality benchmark nor a measurement of how often a real model claims success incorrectly. Passing three tests establishes only these three checked cases.

## Pin and scope

- OpenCode CLI: **1.18.30**
- Release tag commit: **3104c1428ec91f809e5ab86631300de41eb6952e**
- [Official release](https://github.com/anomalyco/opencode/releases/tag/v1.18.30)
- Reference platform: Windows, AMD64, September 13, 2026
- Provider: ephemeral localhost OpenAI-compatible response fixture, no inference
- Fixture: a JavaScript slug function mishandling repeated spaces and tabs

The ordinary `opencode run` path uses `client.session.prompt`, the `/session/{sessionID}/message` endpoint, and `SessionPrompt`. The generated SDK's `v2` directory does not establish that this command uses the separate core Session V2 `/api/session` runtime. The local command can dispatch through an in-process server adapter; this result does not require a separately listening OpenCode server.

## Start here: inspect the recorded result

Clone this repository and check out `dev/vino/opencode-part1-harness` (or the commit linked from the article). From the repository root:

```text
python series/opencode/v1.18.30/labs/01-prompt-to-patch/scripts/verify_reference.py
python series/opencode/v1.18.30/labs/01-prompt-to-patch/scripts/test_lab.py
```

Use `python3` on systems where that is the Python 3 command. The first command requires only Python's standard library. It recomputes the receipt's comparisons instead of trusting its `passed` flag. The second also requires Node.js: it rejects 18 corrupted-evidence scenarios, rejects malformed receipts, and confirms that the unchanged fixture tests fail before the patch and pass after it.

These checks inspect the recorded result and execute the tiny JavaScript fixture. They do **not** run OpenCode, contact a model, or independently authenticate the original recording. CI runs these checks on Windows, macOS, and Linux. The fresh OpenCode reference run is Windows only.

Then read the [claim-to-evidence map](claims.md). It separates what the CLI run observed from what source inspection explains.

## Run OpenCode yourself

Requirements: Python 3, Node.js with `node --test`, and the official OpenCode 1.18.30 executable. No account or provider key is required. Download the executable for your platform from the pinned release. The recorded run used the Windows asset; other operating systems are not yet verified.

From the repository root, with your own executable and private output paths:

```powershell
python .\series\opencode\v1.18.30\labs\01-prompt-to-patch\scripts\run_lab.py `
  --opencode 'D:\tools\opencode.exe' `
  --output 'D:\scratch\opencode-lab-runs'
```

The script creates a unique run directory. Each case starts with the same buggy source and tests. It runs the tests before OpenCode, invokes the real CLI, then runs the tests independently. Exit code 0 from this **lab script** means all its comparisons passed; it is distinct from the CLI exit recorded for each case.

Inspect `receipt.json` first. It records tool names, completed states, returned tool-result counts, file hashes, session count, step finish reasons, and independent verifier results. The run directory also contains private raw tool events and fixture state. Keep those raw files outside the repository. Share only a reviewed, sanitized receipt.

Pass your new receipt to the same offline checker:

```text
python series/opencode/v1.18.30/labs/01-prompt-to-patch/scripts/verify_reference.py /path/to/your/receipt.json
```

The recorded Windows executable came from `opencode-windows-x64.zip` on the official release page. Its downloaded ZIP SHA-256 was `c8c0e0d05ac3dac544a0edfad8de9eb244bf46c6c7a131c38619d40fcf31bd1f`. This records the asset used; it is not a vendor signature.

## Execution boundary

The fixture supplies an isolated OpenCode test home and XDG directories, excludes ambient provider credentials from the child environment, disables project configuration and automatic updates, and enables only the local fixture provider. Tool policy denies actions by default and permits read, edit, and the exact synthetic test command.

This is configuration isolation, not an operating-system sandbox. Tools run with the current user's operating-system authority. The local provider emits only the three fixed actions in the script. The `lab` provider-key value is an inert placeholder accepted by the fixture.

## Inspect the implementation

- [CLI entry and local server adapter](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/cli/cmd/run.ts)
- [Session HTTP handler](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/server/routes/instance/httpapi/handlers/session.ts)
- [Prompt loop](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/prompt.ts)
- [Stream processor](https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/processor.ts)
- [Sanitized Windows reference receipt](reference-results/windows-2026-09-13/receipt.json)

The smallest useful variation is to change the scripted final sentence. Nothing about the workspace or test result should change. A stronger variation is to add an independent test the scripted patch does not satisfy. Neither a convincing final answer nor a green narrow test suite is proof of complete correctness.
