---
created: 2026-10-12
type: ticket
status: implemented
summary: T11 — quizzes MCP tools: connector methods and tools for page reads and quiz create/get/list/delete, plus skill docs.
---

# T11 — Quizzes MCP tools

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Builds on [T10 — Quizzes REST API](10-quizzes-api.md) and extends the
[T6 — pullini-mcp](06-pullini-mcp.md) connector and the
[T7 — Agent Skill API](07-agent-skill-api.md).

## Spec

Extend the `pullini-mcp` connector so an agent can read wiki source and manage
quizzes end to end. Each tool is a thin translation of an MCP call into a T10
REST request (D-25); the connector holds no state between calls.

New tools:

```text
list_pages    list wiki pages, optionally for one project
get_page      fetch one wiki page's source Markdown
create_quiz   create or replace the quiz for one page or artifact
get_quiz      fetch one quiz (questions + scores)
list_quizzes  list your quizzes
delete_quiz   delete a quiz
```

Canonical agent flow: `get_page` → generate up to 10 multiple-choice questions →
`create_quiz` with the page or artifact target (D-42, D-39). The connector's
`skill.md` and the server-served `src/pullini/artifacts/skill.md` (or the T9
`quizzes/skill.md`) document this flow.

Out of scope: submitting attempts via MCP (the owner answers in the web UI),
sharing, anonymous access.

## Plan

1. `mcp/src/pullini_mcp/client.py`: `list_pages`, `get_page`, `create_quiz`,
   `get_quiz`, `list_quizzes`, `delete_quiz`, mapping errors to readable
   `PulliniError`s like the existing methods.
2. `mcp/src/pullini_mcp/server.py`: register the six tools; `create_quiz` takes a
   target (`page` or `artifact`) and a questions list.
3. Refresh skill docs: `mcp/src/pullini_mcp/skill.md` and the API-served skill
   (`src/pullini/quizzes/skill.md`, wired like the artifact skill in T7).
4. Tests: extend `mcp/tests/test_client.py` and `test_server.py` with mocked
   HTTP transport covering the new tools.
5. Wiki: this ticket; link from E6; note the connector version bump / release tag.

## Decisions

D-42 connector gains `get_page`/`list_pages` so quizzes are grounded in page
content; tool surface mirrors the T10 endpoints 1:1 (D-25, D-33).

## Outcome

Shipped.

- `mcp/src/pullini_mcp/client.py`: `list_pages(project=None)`,
  `get_page(project, path)`, `create_quiz(questions, page=None, artifact=None)`,
  `get_quiz(id)`, `list_quizzes()` and `delete_quiz(id)` over the T10 endpoints;
  `_send`/`_request` gained query-`params` support. Paths keep their slashes.
- `mcp/src/pullini_mcp/server.py`: the six tools registered; `create_quiz`
  rejects anything but exactly one of `page`/`artifact` with a readable
  `PulliniError`.
- Skills: the connector's `skill.md` gains a "Quizzes" flow; the API-served
  `src/pullini/artifacts/skill.md` documents the `/api/pages/` and `/api/quizzes/`
  endpoints (extended in place rather than adding a separate endpoint).
- `mcp/README.md`: intro + tools table document the new page/quiz tools.
- Tests: page/quiz cases added to `mcp/tests/test_client.py` (paths, query,
  targets) and `mcp/tests/test_server.py` (registry, delegation, target check).

Verification: `mcp` `uv run pytest` → 42 passed; `mcp` ruff check/format clean;
root `uv run pytest` → 289 passed, 3 skipped; root ruff clean.

Remaining: the connector is prepared for release as `0.8.0` (`mcp/pyproject.toml` +
`__init__.py`) and tagged `mcp-v0.8.0`; pushing the tag publishes via
[Trusted Publishing](06-pullini-mcp.md).
