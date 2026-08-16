# Security policy

These labs interact with agent runtimes, local files, provider authentication, and persisted conversations. Treat generated evidence as potentially sensitive.

## Never publish

- auth.json, auth.lock, cookies, tokens, or environment files
- authorization headers or encrypted provider payloads
- raw provider request or response bodies
- an existing Hermes state database
- personal USER.md, MEMORY.md, SOUL.md, or skills
- unrelated logs from a real profile
- absolute local paths that disclose usernames or private repository names

## Safe execution requirements

- Use a disposable profile created specifically for the lab.
- Use the supplied synthetic markers only.
- Verify the resolved destination before copying or removing files.
- Do not run a provider-backed experiment in CI or an untrusted pull request.
- Do not reuse a work repository containing private source.
- Review generated artifacts before sharing them.

## Reporting a problem

Do not open a public issue containing a credential or private artifact. Use GitHub's private vulnerability-reporting channel if it is enabled for the repository. Otherwise contact the repository owner privately through the profile linked from the repository.

If a credential was committed, revoke it first. Removing it from the latest commit does not remove it from Git history.
