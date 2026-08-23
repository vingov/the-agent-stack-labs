---
name: local-deploy
description: Deploy local lab with HERMES-P3-SKILL-LOCAL-DEPLOY-V1.
---

# Local fixture deployment

Use this procedure only inside the synthetic Hermes Part 3 fixture.

1. Read the supplied durable context for the staging region and the user's dry-run preference.
2. Run the platform's `Test-Lab` or `test.sh` script.
3. Run the platform's `Build-Lab` or `build.sh` script and retain the printed SHA-256 digest.
4. Run the local deploy script with the durable region, a unique run ID, and dry-run mode.
5. Inspect the dry-run receipt and require `dry_run=true`, `deployed=false`, and `network_used=false`.
6. Run the same local deploy script without dry-run mode.
7. Run the verification script with the same run ID and report the verified digest.

Never skip the dry run. Never use a network command. Stop on the first failed check.
