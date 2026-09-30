---
created: 2026-09-30
type: overview
summary: Pullini — read-only Git-backed wiki browser; Python/Django monolith, one admin, projects synced from Git.
---

# Project Overview

**Pullini** is a read-only Git-backed wiki browser. Git repositories are the source of truth; Pullini renders their documentation as browsable, searchable, public read-only pages. Content is never edited in Pullini.

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

- **Project** — a Git repo + branch + docs folder + update interval.
- **Sync** — scheduled (default 10 min) or manual pull, then page regen + index update.
- **Read-only** — one Admin role can manage projects but cannot edit wiki content.
- **Search** — first-class, scoped to current project or all projects.

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

Foundation is implemented — see [E1 epic](epics/epic-01-foundation.md). Subsequent
work is tracked in the same folder.
