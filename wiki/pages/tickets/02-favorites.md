---
created: 2026-10-05
type: ticket
status: implemented
summary: T2 — per-user favorites: star toggle, six most recent on home, and a /favorites/ page.
---

# T2 — Favorites

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Builds on [T1 — Authorization](01-auth-login.md). Raw input:
[01-add-favorites-page.md](../../raw/01-add-favorites-page.md).

## Spec

Logged-in readers can star any generated wiki page and unstar it again. The six
most recently starred pages appear as cards on the home page above the project
list, a "Favorites" link sits beside "Browse projects", and `/favorites/` lists
every starred page. Favorites require login (D-26) and are stored per user as
`Favorite(user, page)`.

## Plan

1. `pullini.favorites` app: `Favorite(user, page, created_at)`, unique per `(user, page)`, ordered newest first, indexed by user + `created_at`.
2. Views/URLs: `GET /favorites/` list; `POST /favorites/toggle/<page_id>/` toggles and returns an HTMX partial (or redirects back when there is no HTMX request); home passes the user's six most recent.
3. Vendor `htmx.min.js` under `static/js/vendor/` and load it from the base template.
4. Templates: star button on the wiki page, `favorites/_star.html`, `favorites/list.html`, and a favorites row on the home page.
5. Tests: toggle create/remove, uniqueness, login required, home shows at most six most recent, list shows all, star state, anonymous rejected.

## Decisions

Favorites reference the derived `Page` row (D-28); HTMX is vendored locally (D-29).
Extends D-26/D-27.

## Outcome

Shipped. New `pullini.favorites` app with `Favorite(user, page)` (unique per pair,
newest first); HTMX star toggle on wiki pages, six most recent on the home page,
and a `/favorites/` list. Verified by `tests/test_favorites.py` (toggle create/
remove, uniqueness, login required, POST-only, home six-item limit, per-user list
scoping, star state on the wiki page).

