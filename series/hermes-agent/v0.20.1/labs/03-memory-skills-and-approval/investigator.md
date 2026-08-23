# Investigator track

## Goal

Instrument the boundary between durable files, prompt construction, tool results, and the provider request.

## Minimum experiment matrix

| Experiment | Mutation | Required evidence |
| --- | --- | --- |
| E0 | Start isolated at the exact pin | tag, commit, platform, model, profile fingerprint |
| E1 | Stage then approve the fact | pending record, pre/post target hash, fresh request marker |
| E2 | Stage then approve the preference | pending record, `USER.md` hash, fresh request marker |
| E3A | Stage then reject memory | pending record plus unchanged durable-tree hash |
| E4 | Stage then reject an incomplete skill | full diff plus unchanged skill-tree hash |
| E5 | Approve and reuse the complete skill | fresh skill-index marker, `skill_view`, terminal and fixture receipts |

## Controls worth adding

- Run the task in an otherwise identical profile without the skill.
- Change only the 60-character routing description and compare skill selection.
- Approve a write in the current process, then compare an ordinary next turn with a brand-new session.
- Repeat with background review enabled and report every trial, including no-write outcomes.
- Create a second isolated profile and prove that its prompt cannot see the first profile's markers.

## Evidence rules

- Treat model output as a claim, not proof.
- Record marker presence and hashes at the provider boundary; do not publish full system prompts.
- Keep raw provider bodies, credentials, and session databases private.
- Report failed attempts. The reference run's overlong-description rejection materially improved the final lab.
- Separate `OBSERVED`, `TEST-BACKED`, `CODE-BACKED`, and `NOT VERIFIED` claims.

Use [expected/claim-matrix.md](expected/claim-matrix.md) as the submission checklist.
