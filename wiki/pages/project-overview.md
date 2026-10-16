---
created: 2026-09-30
type: overview
summary: Pullini — read-only Git-backed wiki browser; Python/Django monolith, user-owned private projects synced from Git.
---

# Project Overview

**Pullini** is a read-only Git-backed wiki browser. Git repositories are the source of truth; Pullini renders their documentation as browsable, searchable, read-only pages. Content is never edited in Pullini. Each project is owned by one user and private to them (T15): owners add and manage their own projects through an in-app page, and only the owner and admins can browse a project and its pages.

Full design: [Pullini V1 — High-Level Design](specs/pullini-v1-hld.md).

## Tech stack

- Python + Django
- Django Templates + HTMX
- Tailwind CSS
- SQLite (default) or PostgreSQL (k3s/production)
- Git CLI / Git library for per-project local clones
- Markdown renderer
- Database-native full-text search (SQLite FTS5 / PostgreSQL FTS)

## Architecture

Single Python monolith (no microservices in V1). Modules: UI/UX, authentication, project management, Git synchronization, Markdown/page generation, search/indexing. Persists to a database plus local Git repositories on disk.

## Key concepts

- **Project** — a user-owned Git repo + branch + docs folder + update interval; name, slug and on-disk clone are scoped per owner.
- **Sync** — scheduled (default 10 min) or manual pull, then page regen + index update.
- **Read-only** — owners (and admins) manage projects via the in-app page and manual refresh, but cannot edit wiki content; a project and its pages are visible only to their owner and admins. Non-staff users log in for per-user state such as favorites.
- **Search** — first-class, scoped to current project or the caller's visible projects.

## Repository layout

```text
pullini/
├── manage.py                  # Django CLI entry point
├── src/pullini/
│   ├── settings.py            # env-driven config (SQLite/Postgres, DATA_DIR)
│   ├── urls.py / wsgi.py / asgi.py
│   └── core/                  # health checks, base views
├── templates/                 # base + page templates
├── assets/css/input.css       # Tailwind v4 source (design tokens)
├── static/                    # source static (built CSS is gitignored)
├── k8s/                       # Kubernetes + FluxCD manifests
├── docker/entrypoint.sh
├── tests/
├── scripts/wiki.mjs           # project wiki helper
└── wiki/                      # this knowledge base
```

Implemented so far: [E1 — Foundation](epics/epic-01-foundation.md),
[E2 — Admin & Projects](epics/epic-02-admin-and-projects.md),
[E3 — Git Synchronization](epics/epic-03-git-synchronization.md),
[E4 — Wiki Generation](epics/epic-04-wiki-generation.md) and
[E5 — Search](epics/epic-05-search.md). [E6 — User Artifacts & Agent Connector](epics/epic-06-user-artifacts-and-mcp.md)
is in progress (login/accounts and favorites first). Subsequent work is tracked in
the same folder.
