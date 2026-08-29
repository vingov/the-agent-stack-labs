# HERMES-P4-PROCEDURE-V2

1. Read `policy/policy-v2.json`.
2. Verify the source SHA-256 and exact allowed output path.
3. Complete a dry run for the same operation before applying.
4. Write the artifact atomically.
5. Verify the deployed SHA-256.
6. Preserve one immutable receipt per attempt and one immutable committed-operation index.
