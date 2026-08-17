# Investigator track

**Time:** 2–4 hours

**Provider account:** Depends on the selected extension

## Objective

Falsify one Part 1 boundary without turning the exercise into a production
messaging test.

## Choose one extension

| Boundary | Safe experiment |
| --- | --- |
| Entry-point isolation | Compare a CLI session with an official gateway test harness |
| Explicit continuity | Exercise handoff into a non-production destination |
| Restart recovery | Use a disposable gateway fixture and the pinned recovery tests |
| Delivery obligation | Inject a send interruption into the official delivery-ledger tests |
| Workspace failure | Move the disposable workspace after persistence, then inspect resume behavior |
| Version drift | Repeat at another exact tag or commit |

## Required evidence

Record only:

- exact Hermes version and commit;
- operating system and architecture;
- session key shape with platform identifiers redacted;
- session ID equality or inequality;
- sanitized workspace labels rather than absolute paths;
- transcript counts and synthetic marker presence;
- delivery states without message bodies;
- PASS, PARTIAL, FAIL, or NOT VERIFIED for each claim.

## Safety rules

- Do not connect the experiment to a production group or support inbox.
- Do not induce failure after a real external side effect.
- Do not publish state.db, session-routing files, credentials, chat IDs, user
  IDs, raw prompts, or provider payloads.
- Do not generalize final-text delivery behavior to every outbound media or
  streaming path.

A failure with a narrow receipt is more useful than a broad success claim.
