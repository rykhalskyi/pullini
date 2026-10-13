---
created: 2026-10-13
type: ticket
status: proposed
summary: T13 — Q&A REST API: token-gated Q&A set CRUD over the T12 domain, mirroring the quizzes endpoints.
---

# T13 — Q&A REST API

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Builds on [T12 — Q&A (core)](12-qanda-core.md) and follows the
[T5 — Artifact REST API](05-artifact-rest-api.md) and
[T10 — Quizzes REST API](10-quizzes-api.md) conventions.

## Spec

Expose the T12 domain over the authenticated JSON API so an agent (via the T14
connector) can create/replace, read and delete Q&A sets. The wiki source the agent
needs to ground a set is already served by the T10 page-read endpoints
(`GET /api/pages/`), so T13 adds only the Q&A resource.

Endpoints (token-gated, owner-scoped, D-32):

```text
GET    /api/qanda/          list your Q&A sets
POST   /api/qanda/          create or replace (upsert) a Q&A set
GET    /api/qanda/<id>/     fetch one Q&A set (questions + answers)
DELETE /api/qanda/<id>/     delete a Q&A set
```

- `POST /api/qanda/` targets exactly one source: `{"page": {"project": "...",
  "path": "..."}}` or `{"artifact": "<slug>"}`, plus an `entries` list. A second
  create for the same owner + target **replaces** the existing set (D-43).
- Each entry is `{"question": "...", "answer": "..."}` (Markdown); the server
  renders and sanitizes `answer_html` on write (D-44).
- There is no attempt/scoring endpoint: a Q&A set is a static document (D-44).

Out of scope: anonymous access, sharing, attempt history, cross-user reads,
generic endpoint unification with quizzes.

## Plan

1. `src/pullini/qanda/api.py`: `qanda_collection` (GET list / POST upsert — `201`
   on create, `200` on replace) and `qanda_item` (GET / DELETE); reuse
   `pullini/api/http.py` helpers (`json_body`, JSON error envelope) and
   `@require_token`; map `QandAError` to `400 invalid_field`.
2. `src/pullini/api/urls.py`: mount `qanda/…` under the `/api/` aggregator.
3. Serializers: list item (`id`, `target_type`, `target`, `item_count`, `stale`,
   timestamps) and detail (adds `{position, question, answer, answer_html}`).
4. Validation via the T12 `validate_entries` service; `_resolve_target` reused
   from the quiz API shape (page honoured through `visible_projects`).
5. Tests `tests/test_qanda_api.py`: 401 without a token, upsert replace,
   owner-scoping (404 for another user's set), malformed bodies, target
   resolution, 405s.
6. Wiki: this ticket; link from E6.

## Decisions

Reuses T12 validation and D-32 bearer auth; mirrors the T10 quizzes endpoints
1:1 (minus attempts). No new decisions.

## Outcome

Not started — plan only.
