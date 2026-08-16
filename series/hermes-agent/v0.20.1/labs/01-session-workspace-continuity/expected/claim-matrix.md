# Claim matrix

| Claim | Reference result | Evidence class | Boundary |
| --- | --- | --- | --- |
| task.txt has the published marker and digest | PASS | OBSERVED | Synthetic file |
| the primary session row persists | PASS | OBSERVED | Hermes storage API |
| the primary session stores workspace-a | PASS | OBSERVED | SQLite session metadata |
| resume resolution returns the primary ID | PASS | OBSERVED | Hermes storage API |
| a fresh session has a distinct ID | PASS | OBSERVED | SQLite session metadata |
| the fresh session stores workspace-b | PASS | OBSERVED | SQLite session metadata |
| the marker belongs only to the primary transcript | PASS | OBSERVED | SQLite message rows |
| the installed CLI lists both sessions | PASS | OBSERVED | sessions list |
| CLI workspace filtering isolates the primary session | PASS | OBSERVED | sessions list |
| a redacted export returns the primary transcript | PASS | OBSERVED | sessions export |
| a live model-tool turn restores the recorded workspace | NOT VERIFIED | NOT VERIFIED | Provider/tool loop |
| CLI and messaging automatically share a conversation | Not expected | CODE/DOC boundary | Entry-point routing |
| gateway restart preserves the intended route | NOT VERIFIED | NOT VERIFIED | Gateway recovery |
| final-text delivery is exactly once | Not claimed | CODE/DOC boundary | Delivery ledger |

The reference result proves a storage and CLI boundary. It does not prove the
unexecuted provider, gateway, or platform-delivery boundaries.
