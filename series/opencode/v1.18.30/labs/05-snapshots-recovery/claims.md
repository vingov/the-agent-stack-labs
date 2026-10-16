# Claim and evidence matrix

| Claim | Evidence | Limit |
| --- | --- | --- |
| First revert restores the selected helper's saved version, including an independent region changed later | Two actual Windows runtime cases; selected patch path, tree/blob bytes, current-file captures | Existing tracked regular helper; first message-level revert after completed work |
| The unrelated later note survives first revert | Same note change in both cases; note absent from patch path list; complete checkpoint manifests | Not a guarantee for repeated revert, unrevert, or all paths |
| Unrevert restores captured pre-undo contents | Pre-undo tree objects match R2; R4 files match those objects | No intervening writer; no arbitrary absent-path or metadata guarantee |
| Correct restoration can fail new behavioral acceptance | Fixed tests fail 2/4 initially and after undo, pass 4/4 after edit and unrevert | Specific formatting behavior; independent display setting checked separately |
| Recovery does not replay the scripted tools here | Captured provider traffic, actual tool records, recovery request ordering | No provider request observed in these intervals; no model inference |
| A plain noReply message cleans the reverted active branch and clears the marker | Separate follow-on on treatment; before/after message IDs, marker, files and provider captures | Not ordinary provider-backed continuation or total historical erasure |
| Stored coding summary and pre-undo comparison describe different intervals | Source plus raw retained coding records and revert diff | No claim about TUI rendering; `/diff` endpoint output is not used as restoration proof |
| Portable offline checks reject contradictory summaries | Reference checker and rejection controls in CI | Consistency, not independent authentication or native runtime execution |

All runtime observations are `OBSERVED_WITH_SCRIPTED_PROVIDER`. The primary comparison is independently checkable without the continuation captures. The implementation's wider capture, error, and restore branches remain `CODE-BACKED` unless this matrix explicitly identifies an observation.
