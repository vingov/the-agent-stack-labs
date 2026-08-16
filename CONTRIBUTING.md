# Contributing

Contributions are welcome when they improve reproducibility, portability, evidence quality, or teaching value.

## Good contributions

- A result from another operating system, provider, model, or pinned release
- A smaller or safer reproduction
- A corrected source permalink
- A version-drift finding
- A new Explorer or Builder explanation
- A test that detects accidental credential or local-state inclusion
- A maintainer-reviewed correction

## Before opening a pull request

On macOS or Linux:

~~~bash
python3 ./shared/python/test_repository_safety.py
bash ./series/hermes-agent/v0.20.1/labs/02-context-and-compression/scripts/test-lab-fixtures.sh
~~~

On Windows with PowerShell 7:

~~~powershell
pwsh .\shared\powershell\Test-RepositorySafety.ps1
pwsh .\series\hermes-agent\v0.20.1\labs\02-context-and-compression\scripts\Test-LabFixtures.ps1
~~~

CI repeats these checks on Windows, macOS, and Ubuntu.

## Result submissions

Start with the **Lab result** issue template. Include only:

- lab ID
- operating system and architecture
- project version, tag, and commit
- provider and model at a high level
- PASS, PARTIAL, FAIL, or NOT VERIFIED per checkpoint
- sanitized hashes, counts, and marker-presence booleans

Never include:

- API keys or OAuth material
- cookies or authorization headers
- raw provider request bodies
- full system prompts
- real USER.md, MEMORY.md, or SOUL.md
- raw session databases
- unrelated environment variables
- absolute home-directory paths

## Evidence language

Use the evidence classes defined in the root README. Do not describe expected, source-backed, or model-reported behavior as OBSERVED.

## Pull requests

Keep one lab or one focused correction per pull request. Explain:

- what changed
- why it changed
- the affected version pin
- how it was verified
- whether the change affects a published article
