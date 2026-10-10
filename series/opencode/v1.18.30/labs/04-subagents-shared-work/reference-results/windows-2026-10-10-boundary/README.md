# Windows delegation-boundary comparison, October 10, 2026

Evidence class: **OBSERVED_WITH_SCRIPTED_PROVIDER**. The real OpenCode v1.18.30 Windows x64 runtime executed six cases through `serve`, supported API session creation, and `run --attach --session`. The model's proposals and report text were prescribed by a local fixture provider. No model inference occurred.

The [receipt](receipt.json) records the policy owner, child creation, actual operation/gate outcomes, bounded marker observations, selected report, current file hashes and fixed test counters. See [the experiment](../../delegation-boundary.md) for the result matrix and reproduction.

The supplied receipt is from a fresh local clone of commit `ca3a6e1daf1fc747a430c5e212c94c90dedae1b3`, with `lab_dirty=false`. It reproduces the earlier development matrix. Both captures were independently reconstructed from raw evidence. Public receipt checks reject 18 contradictory copies; private reconstruction checks reject 18 corrupted capture copies after accepting an unaltered copy. Neither is an independent authentication of historical execution.

Real runtime coverage is Windows x64 only. Portable CI checks the recorded receipt and rejection controls on Windows, macOS and Ubuntu. It does not run OpenCode on those other platforms.
