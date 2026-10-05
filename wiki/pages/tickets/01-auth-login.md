---
created: 2026-10-05
type: ticket
status: implemented
summary: T1 — reader-facing login/logout and the non-staff reader role that favorites build on.
---

# T1 — Authorization: Accounts, Login & Logout

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Provides the account foundation used by [T2 — Favorites](02-favorites.md) (D-26, D-27).

## Spec

Give Pullini a reader-facing authentication surface beside the existing Django
admin: non-staff reader accounts can log in at `/login/`, log out at `/logout/`,
and then browse the public wiki. Accounts are provisioned by staff in the Django
admin — there is no self-service signup. The reader role is the built-in Django
user with `is_staff=False`; no new account model is introduced. Wiki pages stay
public and read-only; authentication only establishes a stable per-user identity
for later features such as favorites.

Out of scope: personal access tokens, artifacts and the MCP connector (the rest
of E6).

## Plan

1. Settings: `LOGIN_URL="/login/"`, `LOGIN_REDIRECT_URL="/"`, `LOGOUT_REDIRECT_URL="/"`.
2. Root URLs: `/login/` and `/logout/` via Django's built-in `LoginView`/`LogoutView`; logout is POST-only.
3. Templates: `registration/login.html` and `registration/logged_out.html`, styled with the existing design tokens.
4. Header: a "Favorites" nav slot; username + Log out when authenticated, Log in otherwise; Settings (`/admin/`) only for staff.
5. Tests: login/logout flow, anonymous redirect to `/login/?next=`, nav variants, non-staff blocked from admin; update the project-refresh test for the new `LOGIN_URL`.
6. Docs: HLD §4 and the project overview reflect the reader role (D-27).

## Decisions

D-27 reader role (extends D-03). Built-in auth views; no custom account model.

## Outcome

Shipped. `/login/` and POST-only `/logout/` use Django's built-in `LoginView`/
`LogoutView`; the reader is a non-staff Django user (no new model). The header now
shows Favorites, the username + Log out, and Settings only for staff.

Verification: `uv run pytest` → 126 passed, 1 skipped; `ruff check`/`format` clean;
`manage.py check` clean; `makemigrations --check` clean (`tests/test_auth.py`).

