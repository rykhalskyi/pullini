---
created: 2026-10-08
type: ticket
status: implemented
summary: T3 — personal access tokens: hashed secrets, a /settings/tokens/ management UI and a @require_token API decorator.
---

# T3 — Personal Access Tokens

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Builds on [T1 — Authorization](01-auth-login.md); used by
[T5 — Artifact REST API](05-artifact-rest-api.md) and [T6 — pullini-mcp](06-pullini-mcp.md).

## Spec

The artifact API is called by agents, not browsers, so it cannot rely on a session
cookie (D-23). Each reader creates a **personal access token (PAT)** in the web UI
and configures it in their MCP client; the token authenticates requests as that
user.

- Tokens are created, listed and revoked at `/settings/tokens/` (login required).
  The secret is shown **once**, at creation; only the public prefix and a hash are
  stored (D-30).
- A token grants the user's full artifact API access — **no scopes** for v1.
- Optional expiry; `last_used_at` is updated on use; revoke is immediate.
- `@require_token` authenticates `Authorization: Bearer <token>` (D-32) and rejects
  missing/invalid/expired/revoked tokens with `401` JSON.

Out of scope: artifacts, the REST API, the MCP connector, token scopes, rate
limiting.

## Plan

1. New app `pullini.accounts` (add to `INSTALLED_APPS`); `PersonalAccessToken`
   (`user`, `name`, `prefix`, `token_hash`, `created_at`, `expires_at`,
   `last_used_at`, `revoked_at`) + migration; admin registration.
2. `pullini/accounts/tokens.py`: secret format `pln_<8 hex>_<43 urlsafe>`;
   `create_for_user(user, name, expires_at=None) -> (token, raw_secret)`; `matches`,
   `is_valid`, `revoke`, `touch_last_used`. Lookup by indexed `prefix`, verify with
   `hmac.compare_digest` over `sha256(secret)`.
3. `pullini/accounts/auth.py`: `@require_token` decorator — parse the Bearer
   header, attach `request.user` / `request.token`, return `401` JSON otherwise.
4. Views/URLs under `/settings/tokens/`: list + create (`POST`) + revoke
   (`POST <id>/revoke/`); login required; render the fresh secret once.
5. Templates `templates/accounts/tokens.html` + `_secret.html`; add a "Tokens"
   link to the account nav in `templates/base.html` for authenticated users.
6. Tests `tests/test_tokens.py`: generation/hash/verify, expiry, revoke,
   `last_used_at`, web CRUD, one-time secret, `401` for missing/bad/expired/revoked.
7. Regenerate the wiki index; record D-30 and D-32.

## Decisions

D-23 PAT over OAuth · D-30 hashed tokens with public prefix, no scopes · D-32 Bearer
authentication. Extends D-27.

## Outcome

Shipped. New `pullini.accounts` app:
- `PersonalAccessToken(user, name, prefix, token_hash, created_at, expires_at,
  last_used_at, revoked_at)` with `is_valid` / `revoke` (migration `0001_initial`).
- `pullini/accounts/tokens.py`: `pln_<8 hex>_<43 urlsafe>` secrets, stored as a
  public prefix + SHA-256 hash (D-30); `create_for_user`, `authenticate` (prefix
  lookup + `compare_digest`), `touch_last_used`.
- `pullini/accounts/auth.py`: `@require_token` bearer decorator sets
  `request.user` / `request.token`, else `401` (D-32).
- `/settings/tokens/` list + create (optional expiry in days) + revoke, secret
  shown once via a session flash; "Tokens" link in the account nav.
- `templates/accounts/tokens.html`; admin registration.

Verification: `uv run pytest` → 151 passed, 1 skipped (`tests/test_tokens.py`, 21
tests); `ruff check`/`format` clean; `manage.py check` and
`makemigrations --check` clean. `uv.lock`'s root version was re-synced from its
stale 0.3.0 to the pyproject 0.5.0 by `uv run`.

