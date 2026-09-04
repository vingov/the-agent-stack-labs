# Reference result: September 4, 2026

## Authoritative evidence

| File | Actual execution | Result |
| --- | --- | --- |
| [local.json](local.json) | Release AIAgent → local terminal, Windows | Both synthetic markers readable |
| [docker.json](docker.json) | Release AIAgent → Docker terminal | Inside readable; sibling `FileNotFoundError` |
| [mounted.json](mounted.json) | Same Docker posture with synthetic sibling mounted read-only | Both markers readable |
| [controls.json](controls.json) | Actual file tools, approvals, stdio MCP and audit discovery, no provider | 13 checks passed |
| [environment.json](environment.json) | Release lockfile environment and model/backend identity | Exact versions recorded |
| [source-tests.json](source-tests.json) | Focused upstream implementation tests | Linux 140 passed; Windows 132 passed, 8 failed |
| [manifest.json](manifest.json) | Synthetic canary and probe hashes | Shared across the three live attempts |

[SHA256SUMS.txt](SHA256SUMS.txt) covers the JSON evidence files. It detects changed bytes; it is not a signature or proof of independent attestation. The [offline verifier](../../scripts/verify_reference.py) also checks semantic consistency, including exact mount inventory and failed-check rejection.

The final live attempts are `release-local`, `release-docker` and `release-mounted`. Each made **2 provider API calls and 1 terminal call**, with exit code zero. The six provider calls describe this reference trio only, not all exploratory runs. The current scripts generated these receipts against an unchanged release source tree and a fresh environment installed with `uv sync --frozen --extra dev --extra mcp --python 3.11`.

Hermes version `0.21.0`, release tag `v2026.8.31`, commit `29112bef099274229cadff79cdff7bf7b99c4b77`; Windows build 26200; Python 3.11.16; Docker Desktop 4.54.0 / Engine 29.1.2; Linux/amd64 image digest in [environment.json](environment.json) and the Docker receipts. Windows Python labels the host as `Windows-10` in `platform.platform()` even though build 26200 is the relevant recorded build identifier.

## What the verifier observed

- Byte-identical probe and canary contents across all three attempts, with fresh receipt names.
- Exactly one requested probe command on the live tool path; terminal was the only enabled toolset.
- Read hashes matched the separately created host manifest. Both host canaries and the probe remained unchanged.
- Docker ran as `65534:65534`, network `none`, not privileged, with `ALL` capabilities dropped and `no-new-privileges`.
- `/workspace` was writable. Eleven additional profile mounts were read-only: skills, attachments, images and eight cache directories. Their actual host sources all matched directories under the disposable lab. The mounted control added only `/outside`, read-only.
- Neither the profile root nor `auth.json` was mounted. The runtime passthrough resolver returned zero forwarded variables. This is not a general credential-exfiltration test.
- Hermes cleanup is asynchronous. The harness waited for its cleanup workers and checked that its session containers were removed.

The host agent retained provider authentication and network access. The Docker process ran only the network-free probe. Selecting a terminal backend did not wrap the entire Hermes process or its in-process extensions.

## Exploratory failures and corrections

1. The first runtime checks used an existing Python environment. The final trio and controls were repeated in the release's fresh locked environment; these final receipts supersede the exploratory measurements.
2. A supporting harness initially expected an inline `python -c` write to succeed. Hermes instead classified the command and denied it under single-query policy. We corrected the harness expectation to match the configured gate and retained the denial as a result. No alternate command was tried to evade that decision.
3. An immediate post-cleanup check failed while Docker cleanup was still running. The final runner retains its own environment handles, waits for `wait_for_cleanup`, then inspects removal. A call returning is not proof that asynchronous cleanup has completed.
4. The original synthetic MCP server used the SDK 1.x `FastMCP` import. The fresh release uses MCP 2.0, so that fixture failed to start. It was updated to the public `MCPServer` API and rerun successfully. This was a fixture compatibility error, not evidence that Hermes's MCP connection was broken.
5. The successful MCP run still emitted `RuntimeWarning: coroutine 'MCPServerTask._watch_stdio_children' was never awaited` from release `tools/mcp_tool.py`. Registration and invocation succeeded; shutdown was requested. The experiment does not establish complete child-process supervision.
6. A first Linux test setup tried to build the editable project on a read-only mount and failed before tests ran. The successful run installed only locked dependencies (`--no-install-project`) and imported the unchanged mounted source through `PYTHONPATH`.

Failed attempts and full conversations remain in ignored local run storage. No failed run is included as a passing authoritative receipt.

## Source-test limits

The same selection ran in Linux Docker and native Windows using release dependencies. All 140 passed on Linux. Eight Windows failures are recorded, rather than hidden behind a passing subset: five POSIX/macOS absolute-path cases, one POSIX permission-mode assertion, one symlink-privilege failure and one environment-key casing assertion. This is a portability finding; no unsupported statement about Windows containment follows from these tests. See [source-tests.json](source-tests.json) for the exact test identifiers.

Upstream tests use test fixtures and mocks. Their green results are separate from actual AIAgent, terminal, file and MCP execution. GitHub CI runs only this lab's portable fixture/verifier tests, never provider calls or upstream security tests.

## Interpretation limits

This is one host and a small sequential synthetic workload, not a statistical or adversarial benchmark. Local Windows and Linux Docker differ in user identity and namespace. The Docker pair gives the narrower mount comparison. Neither a gateway, a remote MCP OAuth flow, a real target-service credential nor an OSV query was exercised. The audit fixture tested discovery from declarations and never installed those declared packages.

We do not claim universal sandbox coverage. A path-specific discrepancy between stable `SECURITY.md` wording and `execute_code` source remains outside the article's claims. We did not contact maintainers or treat a model review score as technical validation.

## Primary sources

- [Release and commit](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.8.31), [security policy](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/SECURITY.md).
- [Profile guide at the release](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/website/docs/user-guide/profiles.md), [current profile guide](https://hermes-agent.nousresearch.com/docs/user-guide/profiles/).
- [Terminal dispatch](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/tools/terminal_tool.py), [Docker environment](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/tools/environments/docker.py).
- [File tools](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/tools/file_tools.py), [file safety](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/agent/file_safety.py), [approval policy](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/tools/approval.py).
- [MCP connection and environment filtering](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/tools/mcp_tool.py), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk), [HTTP authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).
- [Audit component discovery](https://github.com/NousResearch/hermes-agent/blob/29112bef099274229cadff79cdff7bf7b99c4b77/hermes_cli/security_audit.py), [current security guide](https://hermes-agent.nousresearch.com/docs/user-guide/security/).

Rolling documentation was checked September 4, 2026. Release-specific behavior above is anchored to the commit, runtime receipts and identified tests.
