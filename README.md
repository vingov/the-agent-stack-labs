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
| Hermes Agent Architecture | [Context files, prompt snapshots, and compression](series/hermes-agent/v0.20.1/labs/02-context-and-compression/README.md) | v0.20.1 / v2026.8.13 / f80f453 | Reference run published |

The Hermes lab accompanies the practical research behind [The Agent Stack](https://theagentstack.substack.com/). Additional labs will be added as new posts are published.

## Quick start on PowerShell

~~~powershell
git clone https://github.com/vingov/the-agent-stack-labs.git
Set-Location .\the-agent-stack-labs
pwsh .\shared\powershell\Test-RepositorySafety.ps1
pwsh .\series\hermes-agent\v0.20.1\labs\02-context-and-compression\scripts\Initialize-Lab.ps1
~~~

The initializer creates a disposable directory under the operating-system temporary directory. It does not install Hermes, authenticate a provider, or modify an existing Hermes profile.

Continue with the [Hermes setup guide](series/hermes-agent/v0.20.1/setup/README.md).

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
