---
created: 2026-10-04
type: epic
status: proposed
summary: E6 — User accounts, personal access tokens, user-owned Markdown artifacts, the pullini-mcp connector, and favorites.
---

# E6 — User Artifacts & Agent Connector (MCP)

Design: [Pullini V1 — High-Level Design](../specs/pullini-v1-hld.md).
Builds on [E2 — Admin & Projects](epic-02-admin-and-projects.md),
[E4 — Wiki Generation](epic-04-wiki-generation.md) and
[E5 — Search](epic-05-search.md).

## Spec

Users need a place to keep AI-generated artefacts — the same Markdown pages
Pullini already renders, optionally with a Mermaid chart — written and updated by
an AI agent. Artefacts are owned by a user and are **private by default**, with a
revocable **unlisted share link** for read-only viewing.

Because the author is an agent rather than a browser, the credential cannot be a
session cookie. Each user creates a **personal access token (PAT)** in the web UI
and configures it in their MCP client; a local **stdio connector** (`pullini-mcp`,
published on PyPI) translates MCP tool calls into authenticated HTTPS calls to the
Pullini host. No OAuth 2.1 authorization server, dynamic client registration or
ASGI hosting is required in this epic.

The accounts introduced here also let **favorites** graduate from a browser
session to a stable per-user list (raw input:
[01-add-favorites-page.md](../../raw/01-add-favorites-page.md)): star any wiki
page, see the six most recent on the home page, and browse the full list on a
Favorites page.

## Plan

1. **Accounts** — Django built-in username/password login; a non-staff
   reader/owner role beside the existing admin; `/login/` + `/logout/`.
2. **Personal access tokens** — `PersonalAccessToken` (hashed secret, public
   prefix, scopes, optional expiry, `last_used_at`, revoke) with a
   `/settings/tokens/` management UI and a `@require_token` view decorator.
3. **Artifacts (web)** — `Artifact` model (owner, title, slug, Markdown, rendered
   HTML, plain text, content hash, `private`/`unlisted`, share token); rendered
   through the existing `pullini.wiki.markup` pipeline; owner list/detail views
   and a public `/a/<share_token>/` read-only page.
4. **Artifact REST API** — plain Django JSON views under `/api/artifacts/` plus
   `/api/me/`, authenticated with the PAT.
5. **MCP connector** — `pullini-mcp` FastMCP stdio server (`PULLINI_URL`,
   `PULLINI_TOKEN`) exposing `store/list/get/update/delete/share_artifact`;
   packaged on PyPI (`uvx pullini-mcp`) with a Trusted-Publishing workflow.
6. **Favorites** — `Favorite(user, page)`; HTMX star toggle on wiki pages; six
   most recent on the home page; nav link; `/favorites/` page.
7. **(Later)** remote HTTP MCP reusing the same PAT verifier — the only step that
   needs ASGI; not part of this epic's initial delivery.

## Data model

- `PersonalAccessToken(user, name, prefix, token_hash, scopes, created_at, expires_at, last_used_at, revoked_at)`
- `Artifact(user, title, slug, content, html, plain_text, content_hash, visibility, share_token, created_at, updated_at)`
- `Favorite(user, page, created_at)`, unique per `(user, page)`

## Decisions

D-23 PAT over OAuth for agents · D-24 user-owned artifacts with unlisted sharing ·
D-25 local stdio connector on PyPI · D-26 login-only favorites · D-27 non-staff
reader role (extends D-03) · D-30 hashed tokens with public prefix, no scopes ·
D-31 per-user artifact slugs frozen on create · D-32 Bearer auth and API-only share
mutations · D-33 in-repo connector with Trusted Publishing. The deployment server
stays WSGI as in D-09.

## Tickets

- [T1 — Authorization](../tickets/01-auth-login.md) — implemented
- [T2 — Favorites](../tickets/02-favorites.md) — implemented
- [T3 — Personal Access Tokens](../tickets/03-personal-access-tokens.md) — proposed
- [T4 — Artifacts (model & read-only web)](../tickets/04-artifacts.md) — proposed
- [T5 — Artifact REST API](../tickets/05-artifact-rest-api.md) — proposed
- [T6 — pullini-mcp Connector](../tickets/06-pullini-mcp.md) — proposed

## Outcome

In progress. Accounts, login/logout and favorites shipped. Remaining work is split
into T3–T6; none started.
