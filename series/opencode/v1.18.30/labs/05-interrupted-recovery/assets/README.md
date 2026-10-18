# Article figures

These figures describe the recovery boundary demonstrated by the [interruption lab](../README.md). The Mermaid sources are editable. PNGs are native Mermaid Live Editor exports; SVGs preserve the rendered content with editor viewport transforms removed. Line breaks improve phone readability without changing labels or edges. See [manifest.json](manifest.json) for exact asset identities and rendering scope.

## Figure 1

![Stored patch parts select paths and earlier references, while saved Git trees supply their contents. First message-level revert restores only those selected paths within the current working files. Independent checks inspect the full task-relevant file set, including affected paths that revert did not select.](recovery-scope.png)

*Patch records select paths and earlier versions; saved trees supply their contents. Revert changes only the selected paths. The independent check examines the full task-relevant file set, including affected paths not selected by revert, such as the catalogue in the forced-stop case. The separate capture of pre-undo contents for unrevert is omitted. This is not an atomic rollback of files and conversation state. [Recovery selection][revert] · [Snapshot restoration][snapshot]*

[Editable Mermaid](recovery-scope.mmd) · [SVG](recovery-scope.svg)

## Figure 2

![The external lab harness terminates the OpenCode server while the generator waits. Independent observation finds the server exited and generator alive. The lab harness then stops the generator before restarting OpenCode with the same profile. Readback still shows a running stored tool but no live session-status entry. First revert restores only the source and leaves the changed catalogue.](forced-stop-sequence.png)

*Observed forced-stop sequence. The external lab harness stopped the generator before restart and recovery. Its stored `running` value afterward was not evidence of a live process. The status listing and tool record describe different state owners; the diagram does not imply automatic process resumption or a transactional recovery sequence.*

[Editable Mermaid](forced-stop-sequence.mmd) · [SVG](forced-stop-sequence.svg)

[revert]: https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/session/revert.ts#L13-L136
[snapshot]: https://github.com/anomalyco/opencode/blob/3104c1428ec91f809e5ab86631300de41eb6952e/packages/opencode/src/snapshot/index.ts#L318-L545
