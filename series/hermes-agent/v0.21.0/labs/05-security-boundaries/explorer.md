# Explorer: inspect the boundary without a provider

Start at the repository root. You need Python 3.11 or newer. Nothing in this track needs Docker, Hermes, credentials or network access.

## Predict

A process starts in `workspace/`. A marker lives at `../outside/outside.txt`. Does changing the current directory prevent it from reading that marker? What would change if the sibling directory did not exist in the process's filesystem namespace?

## Inspect

Open the [reference results](reference-results/windows-2026-09-04/README.md). Compare `local.json`, `docker.json` and `mounted.json`:

- `probe`: the marker reads and returned hashes;
- `tool_call_names` and `tool_exit_codes`: what the real model/tool path did;
- `containers`: inspected execution settings and relative mount sources;
- `checks`: the host verifier's separate observations.

The readable inside marker is a positive control in every case. Without it, a broken interpreter or wrong working directory could look like successful isolation. Mounting the outside marker back into Docker is another positive control: it demonstrates that the negative read was sensitive to the configured visibility.

## Verify

```text
python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/verify_reference.py
python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/test_lab.py
```

The verifier checks hashes, tool evidence, exact mount destinations and modes, execution settings and required checks. The test suite deliberately leaves `passed: true` while corrupting ten different pieces of evidence. Each corrupted case must be rejected.

This checks a published record's consistency. Its checksum file detects changed bytes; it is not a signed attestation and cannot independently prove that the historical run happened.

## Make a fresh generic control

```text
python series/hermes-agent/v0.21.0/labs/05-security-boundaries/scripts/initialize_lab.py --destination runs/part5/explorer
```

Enter `runs/part5/explorer/workspace` in your shell, then run:

```text
python canary_probe.py --receipt explorer.json
```

Both markers should be readable on an ordinary local filesystem. This step is a generic OS control, **not a Hermes run**. An existing output filename is refused so a second attempt cannot replace the first receipt.

## Challenge

Make a copy of the reference directory under `runs/part5/`. Change the Docker outside result to readable while keeping `passed: true`. Pass that directory with `verify_reference.py --reference YOUR_COPY`. The verifier should fail. Explain why a model's confident summary, a zero exit code and a consistent target receipt are three different kinds of evidence.

Continue with [Builder](builder.md) to produce fresh Hermes receipts.
