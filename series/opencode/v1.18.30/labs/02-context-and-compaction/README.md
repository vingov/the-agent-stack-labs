# Repository context and compaction

**Question:** A file changed, and an old read is still in the session. What reaches the next provider call?

This small lab runs the official OpenCode CLI against a scripted loopback provider. OpenCode discovers instructions, expands a text attachment, executes real reads, stores the conversation, compacts it, and constructs subsequent requests. **No model inference occurs.** The fixture chooses every tool call, reports artificial token usage, and returns a fixed summary. It tests context mechanics, not a model's choices or summary quality.

## Result you can inspect

Both cases use the same files, prompts, reads, and reported usage. Only `compaction.auto` differs. Pruning is disabled in both cases.

| Checkpoint | Automatic compaction disabled | Automatic compaction enabled |
|---|---|---|
| Initial request | Global, root, and configured rules; attached text | Same |
| First real source read | Old source and nested `AGENTS.md` appear as tool output | Same |
| Source changed externally before second invocation | Old observation still sent; new bytes absent | Same |
| After scripted high usage | Full selected history continues | Old head sent to a summary request; recent second turn retained |
| Next ordinary request | Old read still present | Fixed summary plus recent turn; old read absent |
| Final session export | Full old read remains stored | Full old read remains stored |
| Explicit source re-read | New bytes appear; existing nested rule stays in history | New bytes and newly loaded nested rule appear |

The unread file's marker never appears in any request. Root `CLAUDE.md` is also excluded while root `AGENTS.md` is present. These controls concern inclusion, not model compliance.

The old read exceeds 2,000 characters. Its beginning reaches the compaction request, but its end marker and the nested instruction appended after the content do not. This is the compaction serializer's clipping, not the read tool's separate size limit. The raw read output remains complete in storage. The fixed summary intentionally omits all old markers; omission by a real summarizing model was **not** measured.

Read the [claim matrix](claims.md) and [sanitized reference receipt](reference-results/windows-2026-09-25/receipt.json). The receipt contains marker names, message roles/identities, call IDs, hashes and configuration. Raw provider bodies, system prompts, session exports and local paths stay outside Git.

## Check the recorded evidence

From the repository root, with Python 3.10 or later:

```text
python series/opencode/v1.18.30/labs/02-context-and-compaction/scripts/verify_reference.py
python series/opencode/v1.18.30/labs/02-context-and-compaction/scripts/test_lab.py
```

Use `python3` if that is your Python command. The first command should print `"passed": true`. The tests accept the reference and reject 17 missing or contradictory evidence variants, including a forged pass flag. They verify consistency of the recording; they cannot authenticate the historical run.

## Run the actual CLI

Requirements: Python 3.10+, Git, and the official OpenCode **1.18.30** executable from the [official release](https://github.com/anomalyco/opencode/releases/tag/v1.18.30). Choose the release asset for your OS and verify its release-provided digest. No provider account or key is needed. No global installation is required.

From a fresh checkout, substitute absolute paths for the executable and a **private output directory outside the checkout**:

```text
python series/opencode/v1.18.30/labs/02-context-and-compaction/scripts/run_lab.py --opencode /absolute/path/to/opencode --output /absolute/private/output
```

The runner prints a new `context-...` directory and a pass result. Validate that directory independently:

```text
python series/opencode/v1.18.30/labs/02-context-and-compaction/scripts/verify_run.py /absolute/private/output/context-...
```

On Windows, use an absolute path ending in `opencode.exe`. The supplied runtime reference and fresh-checkout execution were tested on native Windows AMD64 only. The Python offline checks use the standard library and have CI jobs configured for Windows, macOS and Ubuntu; those jobs have not been executed remotely for this unpublished package. Cross-platform CLI execution is unverified.

The runner creates two disposable synthetic Git repositories. It isolates application configuration and state, discards inherited provider credentials, allows only the `read` tool, disables external plugins with `--pure`, disables snapshots, language servers, model-list fetching and auto-update, and directs the configured provider to loopback. This is configuration hygiene, not an OS sandbox. It does not operate on your source checkout.

Each case uses these ordinary local CLI commands, with the generated configuration in its environment:

```text
opencode run --pure --format json --model lab/scripted --title "Synthetic context boundary" --file attached.txt -- "Inspect src/slug.mjs. LAB_P2_OLD_REQUEST"
opencode run --pure --format json --model lab/scripted --session SESSION_ID -- "Inspect recent.txt. LAB_P2_TAIL_REQUEST"
opencode run --pure --format json --model lab/scripted --session SESSION_ID -- "Re-read src/slug.mjs. LAB_P2_REREAD_REQUEST"
opencode export SESSION_ID
```

The export is run after each invocation. Between the first and second, the Python fixture replaces the source file. The second invocation receives provider-reported input/output usage of 31,000/1 tokens, deliberately exceeding the configured usable budget. Both cases receive that same report. `tail_turns: 1` and `preserve_recent_tokens: 8000` make the recent-tail comparison explicit; these are lab settings, not claims about defaults.

Keep the generated directory private. It includes full provider requests, CLI streams, session exports, generated configuration, and local OpenCode state. Only `receipt.json` is designed for review as sanitized evidence, and should still be inspected before sharing. Nothing is automatically uploaded or deleted.

## Change one assumption

In a copy of the runner, set `tail_turns` to `0`. Predict which recent-file markers will move into the summary request and disappear from ordinary continuation unless the summary carries them. The reference verifier should reject that altered run because its expected contract is a one-turn tail. Inspect the captures before adapting the checker. This is an optional exercise, not an additional published result.

If a fresh run fails, inspect the printed run directory's CLI stderr/stdout and request inventory. A timeout or missing session export is failure, not a passing empty result. Confirm `opencode --version` is `1.18.30`, Git is available, and the executable can run on your platform. Reruns create new directories; keep the failed evidence for comparison. To clean up, remove only the exact generated directory after closing its processes.

## Scope and provenance

- Source: [v1.18.30 actual commit](https://github.com/anomalyco/opencode/tree/3104c1428ec91f809e5ab86631300de41eb6952e), observed September 25, 2026.
- Current stable at research time: [v1.18.32](https://github.com/anomalyco/opencode/releases/tag/v1.18.32), actual commit `545f51d26cc39a907d2867492d498d9607ea5fa4`. The inspected text context path is unchanged except Bedrock image support, outside this fixture. Continuity therefore remains on 1.18.30.
- Surface: ordinary local `opencode run` through `SessionPrompt`. The SDK v2 directory name does not make this the separate core `/api/session` runtime. Shared helpers imported from core remain part of the actual path.
- The fixed summary can demonstrate substitution and continuation; it cannot demonstrate semantic preservation. Reported usage controls the trigger; it is not the actual request's measured token count.
- Tool-output pruning, large-file read truncation, repeated compaction, media, provider errors, plugins and instruction obedience are not exercised. Their source-backed distinctions are in the claim matrix.
- The [Part One lab](https://github.com/vingov/the-agent-stack-labs/tree/7a0a28f39150b5072f7a326ffd18c69a43340998/series/opencode/v1.18.30/labs/01-prompt-to-patch) establishes the earlier execution boundary. This lab uses a new fixture and does not modify that package.

**Reusable lesson:** Track current files, stored observations, and selected provider input separately. A durable observation can be stale, excluded from continuation, or represented only by a summary. Re-read mutable facts when they matter.
