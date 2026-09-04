# Claim matrix

| ID | Claim | Evidence class | Evidence and limit |
| --- | --- | --- | --- |
| P5-01 | Local terminal reads a synthetic sibling outside cwd | OBSERVED | `local.json`; live model → actual Hermes terminal → hash receipt |
| P5-02 | Unmounted sibling is unavailable in the configured Docker execution | OBSERVED | `docker.json`; readable inside control, outside `FileNotFoundError`, inspected mounts |
| P5-03 | A read-only mount restores sibling read access | OBSERVED | `mounted.json`; same probe and marker hashes; no escape demonstrated |
| P5-04 | Profile selection is state separation, not OS confinement | CODE-BACKED + DOC-BACKED, illustrated by P5-01 | Release profile/security contract; this is not a two-profile confidentiality test |
| P5-05 | File-write root denies this outside `write_file` mutation | OBSERVED | `controls.json`; inside success and outside absence; no claim about all tool paths |
| P5-06 | Single-query deny blocks this flagged inline command | OBSERVED | Real terminal classifier/policy result; no target created or alternate retry |
| P5-07 | Protected instruction write needs a current approval decision on this path | OBSERVED | Scripted deny/once/no-callback sequence; not human UI or permanent-grant testing |
| P5-08 | Stdio tool selection and environment filtering affect the actual child | OBSERVED | Real MCP SDK 2.0 server; two synthetic variable booleans; no remote OAuth test |
| P5-09 | Audit discovery omits unresolved declarations | OBSERVED | Actual discovery over synthetic declarations; nothing installed; no OSV query |
| P5-10 | Selected file/approval/Docker/MCP/audit implementation cases pass on Linux | TEST-BACKED | 140 tests; distinct Windows results in source-tests.json |
| P5-11 | General plugin consent does not sandbox in-process Python | CODE-BACKED + DOC-BACKED | Release plugin/security sources; no Part 5 live plugin test |
| P5-12 | HTTP MCP authorization requires target/audience binding | SPEC-BACKED | MCP authorization specification; not exercised by the stdio control |
| P5-13 | Stored prior approval should be provenance, with permission resolved at action time | DESIGN RECOMMENDATION | A proposed architecture rule, not a universal Hermes guarantee |
| P5-14 | Every Hermes tool runs inside the terminal sandbox | NOT VERIFIED; NOT CLAIMED | Backend coverage must be inspected per path; execute_code-specific policy/source discrepancy omitted |
| P5-15 | Docker prevents all escape, exfiltration or malicious extensions | NOT VERIFIED; NOT CLAIMED | No adversarial benchmark, remote service, real target credential, or gateway tested |

Reference files are under [reference-results/windows-2026-09-04](../reference-results/windows-2026-09-04/README.md). Exact source links are collected there so rolling documentation is not silently treated as release evidence.
