# Lab 05: A separate profile is not a sandbox

A profile selects the state an agent loads. What decides which files its tools can reach?

We asked a real Hermes agent to run a small probe against two synthetic markers. One was in its workspace; the other was in a sibling directory. Then we changed the terminal backend and, finally, one Docker mount.

| Actual Hermes execution | Inside marker | Sibling marker | Independent evidence |
| --- | --- | --- | --- |
| Local terminal on Windows | Readable | Readable | Both hashes matched the host manifest |
| Docker, sibling unmounted | Readable | `FileNotFoundError` | Inside hash matched; host sibling still existed |
| Docker, synthetic sibling mounted read-only | Readable | Readable | Both hashes matched the same manifest |

All three final live runs used the same disposable profile, probe bytes and marker contents. Each made two provider calls and one terminal call. The host verifier checked the files, actual mounts and container posture, and waited for cleanup. The local-to-Docker comparison changes OS identity and filesystem namespace; the two Docker cases differ in the explicit sibling mount. These are configured reachability observations, not an adversarial containment evaluation.

The actual mount inventory matters: Hermes also mounted **11 read-only directories from the disposable profile** for skills, attachments, images and caches. The profile root and provider authentication file were not mounted. All mount sources were checked against the disposable lab directory. The provider connection belonged to the host agent.

## Choose a track

- [Explorer](explorer.md): inspect the supplied receipts and run the offline verifier. Python only, about 15 minutes.
- [Builder](builder.md): run the actual Hermes terminal tool locally and through Docker; optionally add a live model. About 30–60 minutes after installing dependencies.
- [Investigator](investigator.md): exercise actual file guards, scripted approval decisions, a stdio MCP server and dependency discovery. About 45–90 minutes. No model required for these controls.

## Quick start from the repository root

For a fresh checkout of the published Part 5 branch:

```text
git clone --branch dev/vino/hermes-part5-security-boundaries https://github.com/vingov/the-agent-stack-labs.git
cd the-agent-stack-labs
```

Use Python 3.11 or newer (`python3` on systems where `python` is not Python 3):

```text
python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/verify_reference.py
python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/test_lab.py
```

Expected: the three live receipts and 13 runtime control checks are internally consistent; five portable tests pass, including ten deliberately corrupted receipt cases and a cleanup check that rejects Docker errors. This does **not** rerun Hermes. The [Builder track](builder.md) creates fresh target-side evidence.

## What you should learn

1. Separate a state namespace, a starting directory and an execution boundary.
2. Inspect actual mounts, user, network mode and environment forwarding before describing a sandbox.
3. Distinguish tool exposure, a selected approval decision and target-side verification.
4. Explain what stdio environment filtering and dependency discovery do and do not establish.
5. Reject a success flag when its supporting evidence is missing or contradictory.

Read the [claim matrix](expected/claim-matrix.md), [reference environment and limitations](reference-results/windows-2026-09-04/README.md), and [full article](article.md).

The [publishing assets](assets/README.md) include rendered versions of both article diagrams and their editable Mermaid sources.

For a fixed reference, the [experiment snapshot](https://github.com/vingov/the-agent-stack-labs/tree/06d5e934cb06c57e17d1b52e4f28e3628dc6f419/series/hermes-agent/v0.21.0/labs/05-security-boundaries) preserves the runner, receipts and cleanup follow-up independently of later article edits.

## Scope and cost

Explorer is offline and uses only the Python standard library. Builder setup downloads Hermes, Python packages and a Docker image. Direct tool runs require no model; `--live` contacts your configured provider and consumes its quota. The final reference trio used six provider requests in total; setup and exploratory repeats are separate from that count.

The scripts create synthetic targets under a new disposable directory and set `HERMES_HOME` before importing Hermes. Live authentication stays with the host profile. Use a lab provider account if available; never publish its authentication file or raw conversation. The runner does not configure a gateway, publish a report, contact a target service, or test credential exfiltration. The Inspector reports Docker network mode; it does not attempt an egress attack.

The upstream source tests passed **140/140 on Linux in Docker**. On native Windows, 132 passed and eight failed because of POSIX-path/mode expectations, unavailable symlink privilege and environment-key casing. Details are preserved in the reference notes. These tests support specific implementation claims; they do not certify the runtime as secure.
