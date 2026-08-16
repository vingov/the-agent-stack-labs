# Challenges and suggested reasoning

## Challenge 1: Explain the recent-tail result

**Question:** Was TEST_FACT_07 or TEST_FACT_08 lost when its original SQLite row was no longer active?

**Suggested reasoning:** No. The original rows remained compacted and recoverable, and the selected tail remained in live memory and reached the next provider request. The active SQLite projection and live request representation were different.

## Challenge 2: Change the manual tail

Run the same experiment with one and four selected recent exchanges. Predict which facts should survive in live memory, then compare the active SQLite view.

## Challenge 3: Reverse the profile edit

Start a fresh session with COBALT and edit the isolated USER.md back to AMBER. Determine whether the ordinary request retains COBALT and which boundary reveals AMBER.

## Challenge 4: Test version drift

Run the lab against a newer Hermes release without changing the reference files. Report which claims still reproduce and link the new commit.

## Challenge 5: Design a better invariant

Propose an observability field that prevents operators from confusing:

- complete persisted history
- active persisted history
- live selected history
- provider-bound history

Describe who owns the field and when it changes.
