---
created: 2026-10-13
type: ticket
status: proposed
summary: T14 — Q&A MCP tools: connector methods and tools for Q&A create/get/list/delete, plus skill and README docs.
---

# T14 — Q&A MCP tools

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Builds on [T13 — Q&A REST API](13-qanda-api.md) and extends the
[T6 — pullini-mcp](06-pullini-mcp.md) connector and the
[T11 — Quizzes MCP tools](11-quizzes-mcp.md) pattern.

## Spec

Extend the `pullini-mcp` connector so an agent can read wiki source and manage
Q&A sets end to end. Each tool is a thin translation of an MCP call into a T13
REST request (D-25); the connector holds no state between calls. The page-read
tools added in T11 (`list_pages`, `get_page`) already cover grounding.

New tools:

```text
create_qanda   create or replace the Q&A set for one page or artifact
get_qanda      fetch one Q&A set (questions + answers)
list_qanda     list your Q&A sets
delete_qanda   delete a Q&A set
```

Canonical agent flow: `get_page` (or `get_artifact`) → write up to 50
question/answer pairs → `create_qanda` with the page or artifact target (D-42,
D-43). The connector's `skill.md` and the server-served
`src/pullini/artifacts/skill.md` document this flow.

Out of scope: scoring/attempts, sharing, anonymous access, a separate skill
endpoint (the artifact skill is extended in place, as in T11).

## Plan

1. `mcp/src/pullini_mcp/client.py`: `create_qanda(entries, page=None,
   artifact=None)`, `get_qanda(id)`, `list_qanda()`, `delete_qanda(id)`, mapping
   errors to readable `PulliniError`s like the existing methods.
2. `mcp/src/pullini_mcp/server.py`: register the four tools; `create_qanda`
   rejects anything but exactly one of `page`/`artifact` with a readable
   `PulliniError`.
3. Refresh skill docs: `mcp/src/pullini_mcp/skill.md` and the API-served
   `src/pullini/artifacts/skill.md` (extend the "Pages & quizzes" section with a
   "Q&A" subsection).
4. `mcp/README.md`: intro + tools table document the new tools.
5. Tests: extend `mcp/tests/test_client.py` and `test_server.py` with mocked
   HTTP transport covering the new tools.
6. Release: bump `mcp/pyproject.toml` and `mcp/src/pullini_mcp/__init__.py` to
   `0.9.0`; note the tag in the wiki; bump the app version in the root
   `pyproject.toml`.

## Decisions

No new decisions: the connector mirrors the T13 endpoints 1:1 (D-25, D-33) and
reuses the T11 page-read tools for grounding (D-42).

## Outcome

Not started — plan only.
