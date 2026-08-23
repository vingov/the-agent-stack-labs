# Synthetic local deployment fixture

This fixture separates three durable concepts:

- fact: `HERMES-P3-FACT-EU-WEST-2`
- preference: `HERMES-P3-PREF-DRY-RUN-FIRST`
- procedure: `HERMES-P3-SKILL-LOCAL-DEPLOY-V1`

The test, build, deploy, and verify scripts operate only inside this directory. A real local deployment requires a matching dry-run receipt. Both receipt types explicitly report `network_used=false`.
