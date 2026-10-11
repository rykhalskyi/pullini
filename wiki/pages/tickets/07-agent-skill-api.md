---
created: 2026-10-11
type: ticket
status: implemented
summary: T7 — an authenticated /api/skill/ endpoint serving a Markdown agent skill that documents the artifact create/edit/delete/share flow.
---

# T7 — Agent Skill API

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Describes the [T5 — Artifact REST API](05-artifact-rest-api.md); a companion for
[T6 — pullini-mcp](06-pullini-mcp.md).

## Spec

An agent connecting to Pullini needs to know how to create, edit and delete
artifacts without a hand-written prompt per host. Publish that instruction as a
**skill document** served over the API:

- `GET /api/skill/` returns the skill as `text/markdown` (an Agent Skills
  `SKILL.md` with `name` / `description` frontmatter).
- Authenticated with the same PAT bearer token as the rest of `/api/` (D-32).
- The document covers authentication, every artifact endpoint, request/response
  shapes, the frozen-slug rule (D-31) and the error payload.

Out of scope: per-user or per-host tailoring, versioning, MCP tool descriptors.

## Plan

1. Author `src/pullini/artifacts/skill.md` (frontmatter + body).
2. `pullini/artifacts/api.py`: `skill` view reading the file via
   `importlib.resources`, `@require_token` + `GET`-only, served as `text/markdown`.
3. `pullini/api/urls.py`: mount `skill/` under the `/api/` aggregator.
4. Tests `tests/test_artifacts_api.py`: `401` without a token and the Markdown
   body with the endpoint table.
5. Regenerate the wiki index; record D-36.

## Decisions

Plain Markdown served from a repo file (no JSON envelope) · token-required ·
D-32 bearer auth.

## Outcome

Shipped. `GET /api/skill/` (`pullini/artifacts/api.py:skill`) returns
`src/pullini/artifacts/skill.md` as `text/markdown`, token-gated. The document
is an Agent Skills file describing `/api/me/` and the artifact CRUD + share
endpoints with examples. Mounted in `pullini/api/urls.py` as `api:skill`.

Verification: `uv run pytest` → 191 passed, 1 skipped (`tests/test_artifacts_api.py`,
16 tests); `ruff check`/`format` clean; `manage.py check` clean.
