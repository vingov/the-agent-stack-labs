# Investigator track

**Time:** 2–4 hours
**Provider account:** Required for provider-backed observations

## Objective

Attempt to falsify the reference result rather than merely repeat it.

## Required instrumentation

Capture only sanitized forms of:

- system-prompt SHA256 and synthetic-marker presence
- selected-history SHA256 and synthetic-marker presence
- session ID equality before and after compression
- active, inactive, and compacted SQLite row counts
- provider-reported cache-read and cache-write token counts
- tool names and synthetic-marker presence in results
- project version, commit, operating system, model, and provider

Do not publish full prompt or request bodies.

## Experiment variants

Choose one variable at a time:

| Variable | Suggested values |
| --- | --- |
| Operating system | Windows, Linux, macOS |
| Hermes release | Exact reference pin, newer tag |
| Provider | Any supported provider exposing safe metrics |
| Manual tail | here 1, here 2, here 4 |
| Context engine | Built-in versus another supported engine |
| Profile transition | AMBER to COBALT; COBALT to AMBER |
| Nested depth | One versus multiple nested context files |
| Skill pressure | Recent versus older loaded skill result |

## Hypotheses to challenge

1. An ordinary turn preserves the profile marker from the cached prompt.
2. Progressive nested guidance changes history without rebuilding the system prompt.
3. Manual compression keeps the same session ID at the reference pin.
4. The selected recent outer tail survives in live memory.
5. The selected tail is not restored to SQLite's active view at the reference pin.
6. Prompt-hash equality does not imply a provider cache hit.

## Submission format

Use the root result schema and submit:

- PASS, PARTIAL, FAIL, or NOT VERIFIED for each hypothesis
- evidence class for each conclusion
- counts, hashes, and booleans only
- a short explanation of any version drift

A FAIL result with a concrete receipt is more valuable than an unverified PASS.
