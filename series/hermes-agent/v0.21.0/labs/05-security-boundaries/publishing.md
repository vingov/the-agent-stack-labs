# Publishing copy

The complete article is in [article.md](article.md). Use the two [rendered diagrams](assets/README.md) where its Mermaid blocks appear. The GitHub lab is already accessible on the linked Part 5 branch.

## Title and preview

**Article title:** Hermes Agent Architecture, Part 5: A Separate Profile Is Not a Sandbox

**Subtitle:** What profiles, approvals, credentials, and execution boundaries actually control

**SEO title:** Why an Agent Profile Is Not a Sandbox | Hermes Part 5

**SEO description:** Three real Hermes runs show what profiles, approvals and Docker mounts actually control, with a reproducible lab and independent checks.

**Suggested slug:** `hermes-agent-profile-is-not-a-sandbox`

**Subscribe-button text:** Subscribe for more architecture investigations built from running systems, small experiments and evidence you can inspect.

## LinkedIn launch post

I wanted to understand what a “separate profile” actually protects when an agent can run commands.

For the final part of my Hermes architecture series, I gave the agent a fresh profile and two harmless files: one inside its workspace, one beside it.

The local terminal could read both. With Docker, the sibling file became unavailable. I added one read-only mount, and the same probe could read it again.

A profile separates state. A sandbox limits authority.

That matters beyond Hermes. Separate memory and sessions can look reassuring while a tool still has the host account’s access. Approval prompts and tool filters each cover different parts of the request, too.

Part 5 follows those boundaries through real runs, with independent checks and an optional lab you can reproduce.

Which do you inspect first when evaluating an agent’s access: its profile, its tools, or the process running them?

## Link for the launch

Append the actual Substack article URL after publication. Until then, the [full article on GitHub](https://github.com/vingov/the-agent-stack-labs/blob/dev/vino/hermes-part5-security-boundaries/series/hermes-agent/v0.21.0/labs/05-security-boundaries/article.md) is a working preview. The suggested slug above is not a published URL.
