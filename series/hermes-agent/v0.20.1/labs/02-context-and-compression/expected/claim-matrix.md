# Reference claim matrix

Reference: Hermes Agent v0.20.1 at commit f80f453ae0679347e38abc917c7f94f717bf96c5.

| Claim | Reference result | Evidence |
| --- | --- | --- |
| Prompt uses stable, context, and volatile tiers | PASS | CODE-BACKED and OBSERVED |
| Skills index is in volatile at the pin | PASS | CODE-BACKED and OBSERVED |
| Ordinary turns can reuse the cached prompt snapshot | PASS | OBSERVED |
| Root project context can appear at startup | PASS | OBSERVED |
| Nested project context can arrive through a tool result | PASS | OBSERVED in two sessions |
| USER.md edit automatically changes the next ordinary prompt | FAIL as a hypothesis | The next ordinary prompt retained the earlier marker |
| Compression reloads built-in USER.md and MEMORY.md | PASS | OBSERVED |
| Compression can rebuild the prompt in the same session | PASS | OBSERVED |
| Manual command /compress here 2 is valid | PASS | OBSERVED |
| Selected recent tail survives in live memory | PASS | OBSERVED |
| Selected-tail rows are active after the reference compression | FAIL as a hypothesis | Original rows remained compacted and recoverable |
| Provider cache hit can be inferred from prompt hash | FAIL as a hypothesis | Provider usage is a separate receipt |
| Full skill body is loaded with skill_view | PASS | OBSERVED |
| Skill body can later become a reload marker | PASS | TEST-BACKED |
| Summary-failure policy has abort and fallback paths | PASS | CODE-BACKED and TEST-BACKED |

The original article-validation total was 33 PASS, 1 PARTIAL, 0 FAIL, and 0 NOT VERIFIED. The PARTIAL result applied to article wording, not to the central runtime experiment.
