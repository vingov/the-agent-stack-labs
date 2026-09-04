# Investigator: identify each enforcing control

Complete [Builder setup](builder.md) first. This track invokes actual release code, with no model or provider credential. The MCP child is a real subprocess built with the release's MCP SDK 2.0 API.

## Run the controls

```text
uv run --project runs/part5/hermes-source --frozen --extra dev --extra mcp python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/run_controls.py --source runs/part5/hermes-source --destination runs/part5/my-controls
```

Use a new destination each time. Expected: **13 passing checks**.

| Control | Positive evidence | Negative evidence | Limit |
| --- | --- | --- | --- |
| File-write root | An inside file contains the expected bytes | Sibling write returns an error; target stays absent | Tests `write_file`, not every possible write path |
| Unattended command approval | A flagged inline command reaches policy resolution | Single-query deny returns `blocked`; no target created | Does not prove every command is classified |
| Protected instruction file | Scripted `once` commits exact harmless content | `deny` preserves absence; removing callback denies the next write | Real callback path, not a human UI interaction |
| MCP tool selection | Selected tool registers and is invoked | Second tool does not register | No remote-service authorization test |
| MCP environment filter | Explicit synthetic variable present | Unlisted synthetic ambient variable absent | Baseline, XDG and tagged secret-source variables have separate rules |
| Audit dependency discovery | Exact plugin requirement pin discovered | Unversioned requirement and local MCP script unresolved | No installation, OSV query or clean-audit verdict |

The terminal command uses a separate ordinary target. The runner never retries a denied proposal through an alternate route. Approval callbacks are scripted choices for the fixture and are removed after the test; no standing approval is created.

The fixture's `requests==2.32.5` declaration is parser input only. It is never installed or offered as a recommended dependency. The active Hermes environment comes from its release lockfile.

## Known runtime warning

The release emitted an unawaited-coroutine warning from `MCPServerTask._watch_stdio_children` during the actual stdio run. Discovery, filtering and tool invocation succeeded, and shutdown was requested. We did not prove every possible child process lifecycle with this probe. See the [reference notes](reference-results/windows-2026-09-04/README.md) for the earlier SDK compatibility correction and other exploratory failures.

## Focused upstream tests

From the Hermes source directory, use the release environment's Python and a fresh `HERMES_HOME`:

```text
python -m pytest -q tests/tools/test_file_write_safety.py tests/tools/test_single_query_approval_mode.py tests/tools/test_docker_network_config.py tests/tools/test_docker_session_isolation.py tests/tools/test_mcp_tool.py::TestBuildSafeEnv tests/tools/test_mcp_tool.py::TestMCPSelectiveToolLoading tests/hermes_cli/test_security_audit.py --tb=short
```

The selection contains 140 tests. Linux passed all 140. Native Windows passed 132 and failed eight; the exact cases and reasons are in [source-tests.json](reference-results/windows-2026-09-04/source-tests.json). Do not convert a skipped platform case into a pass. Many upstream tests use fixtures or mocks; their result is **TEST-BACKED**, distinct from our actual runtime controls.

## Investigate further

Choose one bounded extension: compare another supported backend with synthetic markers, inspect credential names without values, or examine one release change against the claim matrix. Keep the target, tool path, environment and expected effect explicit.

For a separate live `hermes security audit --json`, document scanned component counts, unresolved surfaces and OSV errors alongside findings. This lab's discovery control deliberately makes no network query and does not supply a security-audit report.

A public result should include only sanitized receipts, exact versions, a small reproduction and its limits. Raw provider conversations, profiles and machine-specific paths stay local.
