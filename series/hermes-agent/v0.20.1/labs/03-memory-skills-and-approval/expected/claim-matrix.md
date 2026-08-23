# Claim matrix

| Claim | Evidence class | Reference status | Boundary |
| --- | --- | --- | --- |
| Environment fact was staged before commit | OBSERVED | PASS | Pending record existed while `MEMORY.md` lacked the marker |
| Approved fact reached durable memory | OBSERVED | PASS | `MEMORY.md` contained the marker after native approval replay |
| Preference followed the user-profile path | OBSERVED | PASS | `USER.md` contained the preference marker |
| Rejected memory changed no durable file | OBSERVED | PASS | Pre/post memory-tree hashes matched |
| Rejected incomplete skill changed no durable skill | OBSERVED | PASS | Pre/post skill-tree hashes matched |
| Approved skill became routable | OBSERVED | PASS | Fresh provider instructions contained its index marker |
| Full skill body was progressively loaded | OBSERVED | PASS | Fresh execution called `skill_view` |
| Approved knowledge was reusable | OBSERVED | PASS | Fresh session completed dry-run, deploy, and verify |
| Local deployment used no network | TEST-BACKED + OBSERVED | PASS | Guard scripts and both receipts reported `network_used=false` |
| Commit always activates in an already-running session immediately | NOT VERIFIED | Not claimed | Use a fresh session as the unambiguous checkpoint |
| Background review will always create a memory or skill | NOT VERIFIED | Not claimed | It is heuristic and must be reported per trial |
