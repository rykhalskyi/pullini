---
created: 2026-10-08
type: ticket
status: implemented
summary: T5 — artifact REST API: plain Django JSON views under /api/ authenticated with a PAT Bearer token.
---

# T5 — Artifact REST API

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Uses [T3 — Personal Access Tokens](03-personal-access-tokens.md) for auth and the
[T4 — Artifacts](04-artifacts.md) model; consumed by [T6 — pullini-mcp](06-pullini-mcp.md).

## Spec

Expose artifacts over an authenticated HTTPS REST API so an agent can create,
list, read, update, delete and share them (D-24, D-25). Requests authenticate with
a PAT sent as `Authorization: Bearer <token>` (D-32); all resources are scoped to
the token's user.

Plain Django JSON views — **no Django REST Framework** — matching the monolith's
minimal-dependency style. The API is the **only** way to mutate artifacts.

Endpoints:

```text
GET    /api/me/                    → user + token metadata
GET    /api/artifacts/             → list own artifacts
POST   /api/artifacts/             → create {title, content, visibility?}
GET    /api/artifacts/<slug>/      → detail (source + rendered html)
PUT    /api/artifacts/<slug>/      → full update {title, content}
PATCH  /api/artifacts/<slug>/      → partial update
DELETE /api/artifacts/<slug>/      → delete
POST   /api/artifacts/<slug>/share/   → enable unlisted sharing, return share_url
DELETE /api/artifacts/<slug>/share/   → revoke sharing
```

Out of scope: bulk operations, pagination beyond a simple cap, token scopes,
webhooks, remote/HTTP MCP transport.

## Plan

1. `pullini/api/` package with a root URL aggregator mounted at `/api/` in
   `pullini/urls.py`; views live beside their models (`accounts`/`artifacts`).
2. JSON helpers: request-body parsing with clear `400`s, consistent error payload
   (`{"error": "..."}`), `@csrf_exempt` + `@require_http_methods` on token endpoints.
3. `GET /api/me/` returns username and the presented token's name/prefix/expiry.
4. Hand-rolled serializers: list item (`slug`, `title`, `visibility`, `share_url`,
   timestamps) and detail (adds `content`, `html`, `plain_text`).
5. Share endpoints flip `visibility`/`share_token` on the owner's artifact only;
   cross-user access returns `404`.
6. Tests `tests/test_artifacts_api.py`: full CRUD, per-user isolation, slug frozen
   after title update, share enable/revoke, method restrictions, and `401`s for
   missing/bad/expired/revoked tokens.
7. Regenerate the wiki index; reference D-25/D-32.

## Decisions

Plain JSON views (no DRF) · D-25 connector calls an authenticated REST API · D-32
Bearer auth and API-only sharing mutations.

## Outcome

Shipped. New `pullini.api` package (`http.py` helpers + `urls.py` aggregator
mounted at `/api/`); views live beside their models:
- `pullini/accounts/api.py`: `GET /api/me/` returns the username and the
  presented token's name/prefix/timestamps.
- `pullini/artifacts/api.py`: `GET|POST /api/artifacts/`,
  `GET|PUT|PATCH|DELETE /api/artifacts/<slug>/`,
  `POST|DELETE /api/artifacts/<slug>/share/`.
- Plain Django JSON views (no DRF); `@require_token` Bearer auth (D-32) and
  `@require_http_methods`; a small `ApiError`/`api_endpoint` pair gives a
  consistent `{"error", "detail"}` payload for `400`s. List is capped at 200
  (no pagination), resources are owner-scoped (`404` cross-user), and the slug
  stays frozen across title updates (D-31). `visibility: "unlisted"` on create
  or `POST .../share/` returns a `share_url`.

Verification: `uv run pytest` → 189 passed, 1 skipped (`tests/test_artifacts_api.py`,
14 tests); `ruff check`/`format` clean; `manage.py check` clean.
