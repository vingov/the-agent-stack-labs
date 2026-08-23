# Course map

The Agent Stack Labs uses one recurring learning loop:

1. **Understand** — read the architecture and name the state boundary.
2. **Observe** — reproduce a controlled transition with synthetic data.
3. **Verify** — inspect runtime, persistence, and provider evidence separately.
4. **Change** — alter one variable and predict the new result.
5. **Contribute** — publish a sanitized result or version-drift finding.

## Hermes Agent Architecture

| Part | Topic | Lab status |
| --- | --- | --- |
| 1 | Gateway, sessions, and the agent loop | Available |
| 2 | Prompt assembly, context files, and compression | Available |
| 3 | Memory, skills, and approval-gated reuse | Available |
| 4 | Tools, plugins, delegation, and persistent work | Planned |
| 5 | Security boundaries, profiles, and safe deployment | Planned |

## Completion levels

### Explorer

A learner can explain the durable source, model-visible representation, owner, and refresh boundary.

### Builder

A learner can create an isolated fixture, execute the supported workflow, and compare observed checkpoints with the reference result.

### Investigator

A learner can instrument the provider request and persistence layer, falsify at least one hypothesis, and submit a sanitized compatibility result.

## Course design rule

A new lab is not complete until it contains:

- learning objectives
- prerequisites, cost, and safety notes
- synthetic fixtures
- a supported execution path
- expected checkpoints
- at least one modification challenge
- evidence classifications
- a sanitized reference result
- troubleshooting and recovery guidance
