---
created: 2026-10-12
type: ticket
status: implemented
summary: T10 — quizzes REST API: token-gated quiz CRUD, attempt scoring and the page-read endpoints an agent needs to generate quizzes.
---

# T10 — Quizzes REST API

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Builds on [T9 — Quizzes (core)](09-quizzes.md) and follows the
[T5 — Artifact REST API](05-artifact-rest-api.md) conventions.

## Spec

Expose the T9 domain over the authenticated JSON API so an agent (via the T11
connector) can create/replace and delete quizzes and read the wiki source it needs
to generate them.

Endpoints (token-gated, owner-scoped, D-32):

```text
GET    /api/quizzes/                 list your quizzes
POST   /api/quizzes/                 create or replace (upsert) a quiz
GET    /api/quizzes/<id>/            fetch one quiz (questions + your scores)
DELETE /api/quizzes/<id>/            delete a quiz
POST   /api/quizzes/<id>/attempts/   submit answers, get the score
GET    /api/pages/                   list wiki pages (?project=<slug>)
GET    /api/pages/<project>/<path>/  fetch one wiki page (source Markdown)
```

- `POST /api/quizzes/` targets exactly one source: `{"page": {"project": "...",
  "path": "..."}}` or `{"artifact": "<slug>"}`, plus a `questions` list. A second
  create for the same owner + target **replaces** the existing quiz (D-39).
- `POST /api/quizzes/<id>/attempts/` takes `{"answers": [int, ...]}`, scores
  server-side and upserts `last_score` / `best_score` (D-40); it returns the score
  and per-question correctness.
- Page-read endpoints return the stored `Page` content (already rendered by E4),
  which the agent needs before generating a grounded quiz (D-42); they are
  read-only and never expose other users' data.

Out of scope: anonymous access, sharing, attempt history, cross-user reads.

## Plan

1. `src/pullini/quizzes/api.py`: `quiz_collection` (GET/POST), `quiz_item`
   (GET/DELETE), `quiz_attempt` (POST), `page_collection` (GET), `page_item` (GET);
   reuse `pullini/artifacts/api/http.py` helpers (`parse_str_list`, JSON error
   envelope) and `@require_token`.
2. `src/pullini/api/urls.py`: mount `quizzes/…` and `pages/…` under the `/api/`
   aggregator.
3. Serializers: quiz detail (target, `source_hash`, `stale`, `last_score`,
   `best_score`, questions with options), list items (target, timestamps, scores),
   page items (`project`, `path`, `title`, `content`).
4. Validation via the T9 `validate_questions` service; map `QuizError` to `400`.
5. Tests `tests/test_quizzes_api.py`: 401 without a token, upsert replace,
   owner-scoping (404 for another user's quiz), scoring, malformed bodies, page
   reads.
6. Wiki: this ticket; link from E6.

## Decisions

Reuses T9 validation and D-32 bearer auth; page-read endpoints are the minimal
source access a grounded quiz generator needs (D-42).

## Outcome

Shipped.

- `pullini/quizzes/api.py`: `quiz_collection` (GET list / POST upsert — `201` on
  create, `200` on replace), `quiz_item` (GET / DELETE), `quiz_attempt` (POST
  scoring), `page_collection` (GET, optional `?project=`) and `page_item` (GET).
  All `@require_token` + `@api_endpoint`, owner-scoped, reusing the T9 validation
  and mapping `QuizError` to `400 invalid_field`.
- `pullini/api/urls.py`: mounted `quizzes/…` and `pages/…` under the `/api/`
  aggregator.
- Serializers: quiz list item (target, `stale`, `question_count`, `last_score`,
  `best_score`, timestamps) and detail (adds questions with `options` /
  `correct_index` / `explanation`); page summary and page detail (source
  `content`). Page reads honour `visible_projects`, so disabled projects 404 for
  non-staff (D-42).
- Tests: `tests/test_quizzes_api.py` (19 tests: auth, create/replace, artifact
  target, owner scoping, attempts scoring, validation, 405s, page list/filter,
  page reads, hidden projects).

Verification: `uv run pytest` → 289 passed, 3 skipped; `ruff check`/`format
--check` clean; `manage.py check` and `makemigrations --check` clean.
