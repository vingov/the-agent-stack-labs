# The Agent Stack Labs

Executable architecture labs and reproducible evidence for [The Agent Stack](https://theagentstack.substack.com/).

The repository turns architecture essays into experiments readers can run, inspect, change, and challenge.

> Read the architecture. Run the system. Break an assumption. Inspect the evidence. Contribute the result.

## What makes these labs different

Every load-bearing claim is assigned an evidence class:

- **OBSERVED** — reproduced in a running pinned system
- **TEST-BACKED** — established by a repository test at the pin
- **CODE-BACKED** — supported by pinned source but not directly reproduced
- **DOC-BACKED** — supported by official documentation
- **ISSUE-BACKED** — reported upstream but not independently reproduced
- **NOT VERIFIED** — not safely established
- **FAIL** — observation contradicts the proposed claim

Model answers alone are never treated as proof of prompt contents, persistence, or provider caching.

## Learning tracks

| Track | Designed for | Provider required? | Typical time |
| --- | --- | --- | --- |
| Explorer | Newcomers and students | No | 20–30 minutes |
| Builder | College students and working developers | Optional | 60–90 minutes |
| Investigator | Experienced engineers and researchers | Yes for live-provider receipts | 2–4 hours |

All tracks study the same system boundary at different depths.

## Available labs

| Series | Lab | Pin | Status |
| --- | --- | --- | --- |
| Hermes Agent Architecture | [Session identity and workspace continuity](series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/README.md) | Installed v0.20.1 / 0c50bdb | Reference run published |
| Hermes Agent Architecture | [Context files, prompt snapshots, and compression](series/hermes-agent/v0.20.1/labs/02-context-and-compression/README.md) | v0.20.1 / v2026.8.13 / f80f453 | Reference run published |
| Hermes Agent Architecture | [Durable memory, reusable skills, and approval gates](series/hermes-agent/v0.20.1/labs/03-memory-skills-and-approval/README.md) | v0.20.1 / v2026.8.13 / f80f453 | Reference run published |

The Hermes labs accompany the practical research behind [The Agent Stack](https://theagentstack.substack.com/). Additional labs will be added as new posts are published.

## Quick start

Choose the commands for your operating system. Both paths create the same
synthetic fixtures in a new disposable directory and never touch an existing
Hermes profile.

### macOS with Bash (recommended reader path)

~~~bash
git clone https://github.com/vingov/the-agent-stack-labs.git
cd the-agent-stack-labs
python3 ./shared/python/test_repository_safety.py
bash ./series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/scripts/initialize-lab.sh
~~~

The same Bash commands work on Linux.

### Windows with PowerShell 7

~~~powershell
git clone https://github.com/vingov/the-agent-stack-labs.git
Set-Location .\the-agent-stack-labs
pwsh .\shared\powershell\Test-RepositorySafety.ps1
pwsh .\series\hermes-agent\v0.20.1\labs\01-session-workspace-continuity\scripts\Initialize-Lab.ps1
~~~

The initializer prints the unique lab path and the two commands needed to enter
the environment. It does not install Hermes or authenticate a provider.

| Platform | Setup shell | Repository safety check | CI coverage |
| --- | --- | --- | --- |
| macOS | Bash 3.2+ | Python 3 | Latest macOS runner |
| Linux | Bash 3.2+ | Python 3 | Latest Ubuntu runner |
| Windows | PowerShell 7 | PowerShell | Windows Server |

The published live-provider reference result was captured on Windows. macOS and
Linux readers run the same fixture and experiment workflow, but should report
their operating system with any result because Hermes behavior can vary by
platform.

Continue with [Part 1: session identity and workspace continuity](series/hermes-agent/v0.20.1/labs/01-session-workspace-continuity/README.md).

## Repository contract

- Synthetic markers only
- A disposable profile for every live experiment
- Exact project version, tag, and commit recorded
- Provider metrics kept separate from local prompt hashes
- Generated runs remain untracked by default
- No credentials, cookies, auth files, or real session databases
- Reference results are sanitized summaries, not raw provider payloads
- Provider-backed workflows are never executed in pull-request CI

## Contributing a result

Run a lab, create a sanitized result document, and open a **Lab result** issue. A maintainer may invite a pull request under community-results after checking the artifact.

Do not upload raw session databases, provider request bodies, system prompts, home-directory paths, or authentication files.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Licensing and attribution

Code is licensed under the [MIT License](LICENSE). Educational prose and diagrams are made available under [CC BY 4.0](CONTENT_LICENSE.md).

Hermes Agent is a separate project owned by its maintainers. This repository is an independent educational and validation project and is not an official Nous Research or OpenAI publication.
