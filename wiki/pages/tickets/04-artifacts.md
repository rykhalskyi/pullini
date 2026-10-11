---
created: 2026-10-08
type: ticket
status: proposed
summary: T4 — user-owned Markdown artifacts: model, read-only list/detail pages, unlisted share links and the Artifacts nav entry.
---

# T4 — Artifacts (model & read-only web)

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Builds on [T1 — Authorization](01-auth-login.md) and the rendering pipeline from
[E4 — Wiki Generation](../epics/epic-04-wiki-generation.md); populated through
[T5 — Artifact REST API](05-artifact-rest-api.md).

## Spec

Readers own **artifacts**: AI-generated Markdown pages, optionally with a Mermaid
chart, that Pullini renders read-only (D-24). The web surface is a window onto
content the agent wrote; it never edits (all mutations happen through the API).

- A new **Artifacts** link sits in the main menu beside **Favorites**; the page
  lists all of the signed-in user's artifacts.
- Each artifact renders through the existing `pullini.wiki.markup` pipeline, so
  Markdown, tables, code and sanitized Mermaid work exactly as in the wiki.
- Artifacts are **private by default**. The owner can view a read-only detail page;
  an existing unlisted share link exposes a public `/a/<share_token>/` page. Share
  creation/revocation is an API mutation only (D-32).
- Slugs are per-user and frozen at creation (D-31) so URLs and API addresses stay
  stable across title edits.

Out of scope: creating/editing/deleting from the web, search, favorites, home-page
surfacing, public listing of other users' artifacts.

## Plan

1. New app `pullini.artifacts`; `Artifact` (`user`, `title`, `slug`, `content`,
   `html`, `plain_text`, `content_hash`, `visibility`, `share_token`, `created_at`,
   `updated_at`), unique `(user, slug)`, ordered `-updated_at`, index
   `(user, -updated_at)`; migration + admin.
2. `pullini/artifacts/services.py`: per-user slug allocation frozen on create;
   `save_artifact` rendering `html` / `plain_text` / `content_hash` via
   `pullini.wiki.markup`; share-token generation and clear.
3. Views/URLs: `GET /artifacts/` list and `GET /artifacts/<slug>/` detail (login
   required, owner-scoped) and public `GET /a/<share_token>/` (unlisted only;
   private → `404`). Detail displays the share URL with a copy button when present.
4. Templates `templates/artifacts/{list,detail,shared}.html` using existing design
   tokens; Mermaid init scripts when `has_mermaid`; add the nav link in
   `templates/base.html`.
5. Tests `tests/test_artifacts.py`: slug freeze/uniqueness, rendering + hash,
   owner isolation, login redirects, share visibility, Mermaid, nav.
6. Regenerate the wiki index; record D-31.

## Decisions

D-24 user-owned artifacts with unlisted sharing · D-31 per-user slugs frozen on
create. Renders through the E4 pipeline (D-17/D-18).

## Outcome

Not started. Planned: `pullini.artifacts` `Artifact` model, owner list/detail pages,
public `/a/<share_token>/` and the Artifacts nav entry, verified by
`tests/test_artifacts.py`.
