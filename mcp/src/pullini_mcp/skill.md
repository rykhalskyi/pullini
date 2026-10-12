---
name: pullini-artifacts
description: Use the Pullini MCP tools to create, read, update, delete and share user-owned Markdown artifacts (notes, reports, Mermaid diagrams) on a Pullini host. Use when persisting AI-generated documents.
---

# Pullini artifacts (MCP)

Artifacts are user-owned Markdown documents (tables, code and `mermaid` diagrams
render). They are **private by default**. Use the tools below; the connector
handles the host URL and token for you — never ask the user for either.

## Tools

- `store_artifact(title, content, visibility="private", slug=None, tags=None)` —
  create, or overwrite when `slug` is given.
- `list_artifacts()` — the artifacts you own.
- `get_artifact(slug)` — source Markdown, rendered HTML and plain text.
- `update_artifact(slug, title=None, content=None, tags=None)` — change the
  title, content and/or tags.
- `delete_artifact(slug)` — delete one.
- `share_artifact(slug, enable=True)` — enable/revoke the unlisted `share_url`.
- `list_tags()` — your tag vocabulary (`name`, `slug`, `count`).
- `delete_tag(tag)` — delete a tag by slug, everywhere.

## Workflow

1. Create with `store_artifact`; note the returned `slug` — it is **frozen**, so
   later edits use the slug, not the title (renaming keeps the slug).
2. Edit with `update_artifact(slug, ...)`.
3. Share with `share_artifact`; anyone holding the `share_url` can read it.

## Authoring

- `content` is Markdown; fenced ` ```mermaid ` blocks render as diagrams. Raw
  HTML is sanitized.
- Keep `title` short; put structure in the Markdown headings.
- `visibility` is `"private"` (default) or `"unlisted"`.
- `tags` are plain string labels (≤50 chars, ≤20 per artifact) kept in a
  per-user vocabulary. Passing `tags` replaces the whole set; `[]` clears it.
  Use `list_tags()` to discover existing names.
