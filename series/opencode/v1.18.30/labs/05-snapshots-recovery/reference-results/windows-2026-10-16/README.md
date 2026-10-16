# Windows recovery reference

The sanitized receipt is reconstructed from private raw captures by `scripts/verify_run.py`. It contains file digests, test counts, snapshot identities, and bounded record/request observations. It omits provider bodies, system prompts, home paths, and session databases.

Recorded environment: native Windows x64, OpenCode 1.18.30 official executable, Node 24.13.0, Git 2.52.0.windows.1, Python 3.12.14. A scripted loopback provider generated four main requests per case and no auxiliary requests. No provider calls occurred during revert, unrevert, or the separate noReply continuation.

The final reference is produced from a clean local clone of the lab commit identified in `runtime.lab_revision`. `lab_dirty: false` concerns that lab directory at execution time. It does not authenticate the historical run. The published portable checker verifies internal consistency; fresh runtime reproduction is a separate command in the lab README.

There were no failed OpenCode cases in the initial run. During checker development, the Node text-reporter symbol required a parser correction and a corruption-test script had a syntax error. Both were corrected before the clean reproduction. Those were checker-development failures, not runtime recovery failures. Private captures from the initial run were retained.

A later review tightened checkpoint observation intervals and bounded Git subprocesses, including preservation of partial output on timeout. The reference above comes from another clean local clone at `488c695623d0d5b2428b3fc22265c504b0779374`, after those repairs. Both primary cases and the separate continuation passed raw verification again. All 18 altered-capture controls were rejected, while unmodified full and primary-only copies passed. The two-second Python-child timeout diagnostic test also passed. Earlier captures and their original runner identities were retained separately.
