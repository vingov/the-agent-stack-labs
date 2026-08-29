# Script guide

| Script | Purpose |
| --- | --- |
| `Initialize-Lab.ps1` / `initialize-lab.sh` | Copy the synthetic fixture into a new or empty directory |
| `Test-LabFixtures.ps1` / `test-lab-fixtures.sh` | Check fixture size, digest, policy, and Python syntax |
| `Run-Controls.ps1` / `run-controls.sh` | Execute the seven network-free controls |
| `run_contract.py` | Enforce policy and write attempt/operation evidence |
| `verify_operation.py` | Verify a committed operation independently |
| `render_commands.py` | Produce exact dry-run, apply, and verify commands as JSON |
| `seed_goal.py` | Pin-specific Investigator helper that seeds a goal contract and gate into a disposable Hermes session |
| `run_plugin_probe.py` | Use the pinned real `PluginManager` to discover a synthetic read-only plugin, invoke its tool and hook, and verify unload cleanup |

`seed_goal.py` and `run_plugin_probe.py` import Hermes internals at the pinned version. They are instrumentation for the reference experiment, not promises of stable public API compatibility.

Run every experiment in a newly initialized workspace. Attempt IDs and operation records are intentionally immutable, so rerunning the same IDs in the same directory is expected to be rejected or suppressed.
