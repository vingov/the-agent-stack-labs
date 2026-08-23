# Explorer track

## Goal

Run the deterministic procedure without Hermes, then use the receipts to learn what the provider-backed experiment had to prove.

## 1. Create a disposable copy

Use the initializer from the [lab README](README.md). Change into the printed `workspace/hermes-part3-lab` directory.

## 2. Run the procedure

macOS or Linux:

~~~bash
bash ./scripts/test.sh
bash ./scripts/build.sh
bash ./scripts/deploy-local.sh --region eu-west-2 --run-id P3-EXPLORE-0001 --dry-run
cat ./receipts/P3-EXPLORE-0001.dry-run.json
bash ./scripts/deploy-local.sh --region eu-west-2 --run-id P3-EXPLORE-0001
bash ./scripts/verify.sh P3-EXPLORE-0001
~~~

Windows:

~~~powershell
pwsh -NoProfile -File ./scripts/Test-Lab.ps1
pwsh -NoProfile -File ./scripts/Build-Lab.ps1
pwsh -NoProfile -File ./scripts/Deploy-Local.ps1 -Region eu-west-2 -RunId P3-EXPLORE-0001 -DryRun
Get-Content ./receipts/P3-EXPLORE-0001.dry-run.json
pwsh -NoProfile -File ./scripts/Deploy-Local.ps1 -Region eu-west-2 -RunId P3-EXPLORE-0001
pwsh -NoProfile -File ./scripts/Verify-Lab.ps1 -RunId P3-EXPLORE-0001
~~~

## 3. Check the boundary

The local scripts prove that the procedure is deterministic and guarded. They do **not** prove that Hermes persisted, routed, loaded, or reused anything. Compare your local receipts with the [reference result](reference-results/windows-2026-08-23/README.md).

## Modification challenge

Try the real deploy with a new run ID before its dry run. Predict the result first. The expected failure is `dry-run receipt required`; no staging artifact should be created for that run ID.
