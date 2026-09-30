---
created: 2026-09-30
type: epic
status: implemented
summary: E5 — Search: project and global scopes, contextual snippets, db-native backends (Postgres FTS).
---

# E5 — Search

Design: [Pullini V1 — High-Level Design](../specs/pullini-v1-hld.md) (§9).
Builds on [E4 — Wiki Generation](epic-04-wiki-generation.md).

## Spec

Search is first-class. At minimum two scopes — **current project** and **all
projects** — covering page titles, content, paths and project names, with
contextual snippets and the project/page location. The index must stay current
as project content changes. No Elasticsearch/OpenSearch; use database-native
full-text search where practical, abstracted so both installation types work.

## Plan

1. `pullini.search` package with a backend interface (`get_backend()`).
2. `SimpleSearchBackend`: portable ORM matching (title/path/body/project name).
3. `PostgresSearchBackend`: native `SearchVector`/`SearchRank` via
   `django.contrib.postgres` (no extra infrastructure).
4. `search_pages(query, project=None)` service; Python-side snippets.
5. Views/URLs: global `search/` and scoped `search/<slug>/`.
6. Header search form (all projects) + a scoped search box on wiki pages.
7. Results page with project/path context and snippets.
8. Tests, including a PostgreSQL-only full-text test (run by the CI matrix).

## Outcome

Shipped. `uv run pytest` → 75 passed, 1 skipped (Postgres-only, run in CI);
ruff clean. Verified against `byebyemoneylist`: `dashboard`, `quick purchase`
and `sync` return correctly ranked results.

Key files:

- [`src/pullini/search/backends.py`](../../../src/pullini/search/backends.py)
- [`src/pullini/search/services.py`](../../../src/pullini/search/services.py)
- [`src/pullini/search/views.py`](../../../src/pullini/search/views.py)
- [`templates/search/results.html`](../../../templates/search/results.html)

Deviations: on SQLite, V1 uses the portable ORM backend rather than FTS5 (see
D-21); the derived `Page` table is the index, so it is always current without a
separate index store (see D-22).

## Decisions

D-21 backend abstraction with Postgres native FTS · D-22 Page table is the index.

## Next

E6 — UI/UX shell (remaining navigation polish).
