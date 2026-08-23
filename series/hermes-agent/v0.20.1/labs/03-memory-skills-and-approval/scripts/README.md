# Script reference

| Purpose | macOS/Linux | Windows |
| --- | --- | --- |
| Create disposable lab | `initialize-lab.sh` | `Initialize-Lab.ps1` |
| Validate fixtures and local workflow | `test-lab-fixtures.sh` | `Test-LabFixtures.ps1` |
| Test app | fixture `test.sh` | fixture `Test-Lab.ps1` |
| Build deterministic artifact | fixture `build.sh` | fixture `Build-Lab.ps1` |
| Dry-run or deploy locally | fixture `deploy-local.sh` | fixture `Deploy-Local.ps1` |
| Verify receipts and digest | fixture `verify.sh` | fixture `Verify-Lab.ps1` |

All generated artifacts, receipts, and local staging files remain inside the disposable workspace. The repository fixture is copied before smoke tests so tracked files stay unchanged.
