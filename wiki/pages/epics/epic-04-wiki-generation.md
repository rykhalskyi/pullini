---
created: 2026-09-30
type: epic
status: implemented
summary: E4 — Markdown docs from the clone become read-only pages with tree/index/recent navigation.
---

# E4 — Wiki Generation

Design: [Pullini V1 — High-Level Design](../specs/pullini-v1-hld.md) (§8, §10, §11).
Builds on [E3 — Git Synchronization](epic-03-git-synchronization.md).

## Spec

Turn the configured documentation folder of each project's clone into read-only
wiki pages: headings, links, images/assets, code blocks, tables, lists (HLD §8).
The original Git files remain authoritative; Pullini generates presentation, not
content. Provide tree / index / recent navigation and a clean reading view with
breadcrumbs, title, content, source path and last update (HLD §10, §11).
Out of scope: search (E5), the full navigation shell (E6).

## Plan

1. `pullini.wiki` app with a `Page` model (path, url_path, title, content, html,
   plain_text, content_hash) — derived and regenerable.
2. `wiki/markup.py`: Python-Markdown rendering, title extraction, plain-text
   extraction, and rewriting of relative `.md` links and asset `src`.
3. `wiki/generation.py`: scan the docs folder, upsert changed pages, delete
   pages whose files disappeared; idempotent via content hash.
4. Views/URLs: tree, flat index, recent, page, and read-only asset serving.
5. Regenerate after a sync detects a changed commit.
6. `manage.py generate_pages` for manual regeneration.
7. Templates + content styling; project page links to the wiki with a page count.

## Outcome

Shipped. `uv run pytest` → 62 passed; ruff clean. Verified against a real repo:
`byebyemoneylist` produced **31 pages**, and tree / recent / page views render.

Key files:

- [`src/pullini/wiki/models.py`](../../../src/pullini/wiki/models.py)
- [`src/pullini/wiki/markup.py`](../../../src/pullini/wiki/markup.py)
- [`src/pullini/wiki/generation.py`](../../../src/pullini/wiki/generation.py)
- [`src/pullini/wiki/views.py`](../../../src/pullini/wiki/views.py)
- [`templates/wiki/`](../../../templates/wiki)

Deviations: content styling is hand-written rather than the Tailwind typography
plugin; page URLs use the source path without extension, with `index/`,
`recent/` and `assets/` reserved (see D-17–D-19).

## Decisions

D-17 Markdown via Python-Markdown + hand-written styles · D-18 pages are derived
DB metadata · D-19 path-based page URLs with rewritten relative links.

## Next

E5 — Search.
