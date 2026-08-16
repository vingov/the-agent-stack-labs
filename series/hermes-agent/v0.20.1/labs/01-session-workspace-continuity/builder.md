# Builder track

**Time:** 45–60 minutes

**Provider account:** Required only for the live extension

## 1. Establish the provider-free baseline

Complete the [Explorer track](explorer.md). Preserve the disposable lab and its
environment variables.

## 2. Authenticate the disposable profile

Only if you want the live extension:

~~~text
hermes auth login openai-codex
hermes auth status openai-codex
~~~

Authentication is written to the disposable HERMES_HOME. Never copy its auth
file into the repository or a result submission.

## 3. Start a live session in workspace-a

Change into workspace-a and run:

~~~text
hermes chat --pass-session-id -t file,terminal
~~~

Ask:

~~~text
Read task.txt. Return its exact marker and SHA-256 digest, then report the
current working directory. Use tools for the file and digest; do not guess.
~~~

Record the session ID displayed by Hermes, but do not publish a raw transcript
or absolute path.

## 4. Resume from the other workspace

Exit Hermes, change the shell's directory to workspace-b, and resume the
recorded session without `--in` or `--no-restore-cwd`:

~~~text
hermes chat --resume <session-id> -t file,terminal
~~~

Ask Hermes to report the current working directory and the previously observed
marker. Inspect `hermes sessions list --workspace workspace-a` and a redacted
session export as independent evidence.

Expected at the tested v0.20.1 boundary: explicit resume selects the same
conversation, and the recorded workspace-a context is restored when it still
exists.

## 5. Compare a fresh session

Exit, enter workspace-b, and start a new chat without a resume flag. Record the
new session ID. It should not equal the primary session ID.

Do not use the model's memory claim as the deciding evidence. Compare session
IDs, stored workspace metadata, and redacted transcript membership.

## 6. Classify honestly

- Provider/tool evidence can be OBSERVED only if you completed the live run.
- Storage and sessions-CLI evidence can be OBSERVED from the provider-free
  probe.
- Gateway routing, handoff, restart recovery, and delivery remain NOT VERIFIED
  unless you run the Investigator extension.
