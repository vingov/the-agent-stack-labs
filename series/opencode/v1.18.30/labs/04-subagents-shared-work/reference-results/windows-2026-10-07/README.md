# Windows reference: October 7, 2026

One real OpenCode v1.18.30 CLI invocation used a scripted loopback provider. There was no model inference. The runtime created a fresh `general` child linked to the parent, ran two child reads and one child edit, returned selected text, then ran the parent's fixed test command.

The independent reader saw `return label.trim();` in the shared fixture before the provider released the child's final report. The test file was unchanged at that checkpoint and at completion. Initial tests had two passes and two failures. The parent and external after-run checks each had four passes and no failures.

Seven provider requests were captured: three parent requests and four child requests. There were no auxiliary calls in this reference. The child requests omit the parent-only marker. The supplied handoff marker is present in every child request. The helper's observation marker enters child input through read feedback and is absent from the selected task return and first parent continuation.

The [receipt](receipt.json) is a sanitized reconstruction, not raw provider content. Directory values use the alias `workspace` only after the private verifier compares actual paths. Permission paths under the fresh private run use `<run>`. Session identities remain intact to permit relationship checks. Provider authorization headers are never captured. Token counters from scripted responses are not published as model usage evidence.

The recorded lab checkout was dirty during development. Its Git revision identifies the base checkout, while the runner digest and fixture digests identify the exercised files. The public fresh-checkout procedure is validated separately. Raw captures remain private.

Run `scripts/verify_reference.py` from the lab, or follow the [entry instructions](../../README.md). Receipt checks verify consistency, not historical authenticity. Portable CI does not demonstrate real OpenCode behavior on macOS or Linux.
