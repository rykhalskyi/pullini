---
created: 2026-09-30
type: epic
status: implemented
summary: E2 — admin auth and the Project model: CRUD via Django admin, public read-only project list/overview.
---

# E2 — Admin & Projects

Design: [Pullini V1 — High-Level Design](../specs/pullini-v1-hld.md) (§4, §5, §11).
Builds on [E1 — Foundation](epic-01-foundation.md).

## Spec

Give Pullini its one admin role and its primary organisational unit: the
**Project** (a Git repo + branch + docs folder + update interval). The admin must
be able to add, configure, enable/disable and delete projects, while all wiki
content stays public and **read-only** (no content editing in Pullini, HLD §4).

Out of scope: Git clone/pull and scheduling (E3), Markdown/page generation (E4),
search (E5), full navigation shell (E6).

## Plan

1. `pullini.projects` app with the `Project` model (Git URL validation, unique
   slug, defaults: branch `main`, folder `docs`, interval 10 min, enabled).
2. Register `Project` in Django admin (CRUD, filters, search, slug prepopulation).
3. Public read-only views: project list + overview page; disabled projects hidden
   from anonymous visitors but visible to staff.
4. Templates using the design tokens; home lists projects.
5. Real project counts in `/healthz`.
6. Tests for model/defaults/validation, visibility rules and admin access.

## Outcome

Shipped. `uv run pytest` → 27 passed; `ruff` clean; `manage.py check` clean.

Key files:

- [`src/pullini/projects/models.py`](../../../src/pullini/projects/models.py)
- [`src/pullini/projects/admin.py`](../../../src/pullini/projects/admin.py)
- [`src/pullini/projects/views.py`](../../../src/pullini/projects/views.py)
- [`templates/projects/`](../../../templates/projects)

Deviations: skipped a custom "Refresh now" control until E3 provides the
behaviour; the project overview's Wiki/Activity areas render as empty states.

## Decisions

D-12 management via built-in Django admin · D-13 slug URLs + Git URL validation.
See [`decisions.md`](../../decisions.md).

## Next

E3 — Git synchronization.
