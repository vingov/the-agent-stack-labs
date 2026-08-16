# Explorer track

**Time:** 20–30 minutes
**Provider account:** Not required

## Goal

Explain why changing a durable file does not necessarily change the next model request.

## Step 1: Identify the representations

Read the [reference result](reference-results/windows-2026-08-15/README.md) and classify each object:

| Object | Durable? | Model-visible? | Owner |
| --- | --- | --- | --- |
| USER.md on disk | Yes | Only after loading into a prompt or tool result | Profile |
| Cached system prompt | Persisted/reusable | Yes | Agent runtime |
| Enriched tool result | Session history | Yes while selected | Tool/history path |
| SQLite compacted row | Yes | Not necessarily active | Session store |
| Provider cache receipt | Provider metadata | No | Provider |

## Step 2: Follow AMBER to COBALT

Explain this sequence:

1. Session starts while USER.md contains AMBER.
2. Hermes builds a prompt containing AMBER.
3. USER.md changes to COBALT on disk.
4. An ordinary request still uses the cached prompt containing AMBER.
5. Manual compression reloads USER.md.
6. Hermes rebuilds the prompt with COBALT.

## Step 3: Explain the tail mismatch

The reference compression used:

~~~text
/compress here 2
~~~

The selected recent tail remained in live memory and reached the next provider request. Its original SQLite rows remained compacted rather than active.

Answer:

1. Was the recent information lost?
2. Was the live model-visible history identical to SQLite's active view?
3. Which artifacts would you inspect before claiming data loss?

Suggested reasoning is in the [challenge guide](challenges/README.md).

## Knowledge check

- Why is a prompt hash not proof of a provider cache hit?
- Why is a complete transcript not necessarily the next request?
- Why should a write API distinguish disk success from model visibility?
- Which marker demonstrates progressive context discovery?
- Which marker demonstrates full skill loading?
