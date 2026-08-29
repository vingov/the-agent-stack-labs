# Hermes Agent Architecture labs

This course season studies a real, version-pinned Hermes Agent runtime rather than a moving conceptual target.

## Version policy

Each lab lives under the Hermes version it was tested against. Claims made for one pin do not automatically apply to newer releases.

Published reference pins:

- Part 1 installed-runtime probe: v0.20.1 / release label 2026.8.13 /
  0c50bdbdea57f3d63571e58ae70b3520c4f8b62e
- Part 2 provider-backed run: v0.20.1 / tag v2026.8.13 /
  f80f453ae0679347e38abc917c7f94f717bf96c5
- Part 3 provider-backed run: v0.20.1 / tag v2026.8.13 /
  f80f453ae0679347e38abc917c7f94f717bf96c5
- Part 4 provider-backed run: v0.20.6 / tag v2026.8.27 /
  5fc308a70719a83cccdbba4c0e39c23f5a8239d5
- Reference operating system: Windows, AMD64
- Reference Python: 3.11.16

The commit is part of each evidence boundary even when the displayed Hermes
version is unchanged. These values describe the published reference runs, not a
Windows-only requirement. The public lab harness has native PowerShell and Bash
entry points, and CI validates fixture setup on Windows, macOS, and Ubuntu. New
results should always identify their operating system and architecture.

## Season map

1. Gateway, sessions, and the agent loop
2. Prompt assembly, context files, and compression
3. Memory, skills, and the self-improvement loop
4. Tools, plugins, delegation, and persistent work
5. Security boundaries, profiles, and safe deployment

Parts 1–4 now have runnable labs. Each later lab keeps a network-free Explorer
path while publishing a sanitized provider-backed reference result for the
boundaries that require a live agent.
