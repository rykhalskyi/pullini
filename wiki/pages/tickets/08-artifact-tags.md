---
created: 2026-10-12
type: ticket
status: implemented
summary: T8 — artifact tags: a persistent per-user tag vocabulary, web editing, REST/MCP support and tag filtering.
---

# T8 — Artifact Tags

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Extends the [T4 — Artifacts](04-artifacts.md) model, the
[T5 — Artifact REST API](05-artifact-rest-api.md) and the
[T6 — pullini-mcp](06-pullini-mcp.md) connector.

## Spec

Users want to label artifacts so they can organise and filter them (raw input:
[02-tags-for-artefacts.md](../../raw/02-tags-for-artefacts.md)): tags are plain
string labels, settable and removable both through an agent (MCP/REST) and in the
web UI, with **no separate tag-management screen**, and artifacts can be filtered
by tag.

Locked decisions:

- Tags form a **persistent, per-user vocabulary** created lazily on first use
  (D-37). A tag keeps existing with zero artifacts until its owner deletes it.
- Artifact **content** stays API-only (D-24), but **tags are user metadata** the
  owner may edit from the web (D-38).

- Tag names are trimmed, whitespace-collapsed and capped at 50 characters; the
  display case is preserved and the case-folded slug is the stable identity.
  At most 20 tags per artifact; within a request names are deduplicated.
- Web: attach/detach chips on the artifact detail page and delete a tag from the
  list filter strip, all HTMX-posted and owner-scoped.
- REST: `tags` on create/PUT/PATCH (PATCH may be tags-only), `?tag=<slug>`
  filtering, and `GET`/`DELETE` on `/api/tags/`.
- MCP: `store_artifact`/`update_artifact` accept `tags`, plus `list_tags` and
  `delete_tag` tools.

Out of scope: tag renaming, tag colouring/metadata, cross-user/shared tag
vocabularies, tag-based search facets.

## Plan

1. Models (migration `0002`): `Tag(user, name, slug, created_at)`, unique
   `(user, slug)`, index `(user, name)`; `Artifact.tags` M2M; admin registration.
2. Services: `normalize_tag`, `TagError`, `validate_tags`, `resolve_tags`,
   `set_artifact_tags`, `add_tags`, `remove_tags`, `delete_tag`,
   `tags_with_counts`; `create_artifact` accepts `tags`.
3. REST: `tags` in list/detail serializers; validate list-of-strings; replace the
   tag set when the key is present; `?tag=` filter; `/api/tags/` GET + DELETE.
4. Web: `tag_add`/`tag_remove`/`tag_delete` views and URLs; tag filter on the
   list; `_tags.html` and `_tag_filter.html` partials wired into list/detail/shared.
5. MCP: client `list_tags`/`delete_tag` and `tags` params; server tools;
   refresh both skill documents.
6. Tests: new `tests/test_artifact_tags.py`; extend the artifact and API suites;
   extend the MCP client/server tests.
7. Wiki: this ticket; link from E6; record D-37/D-38.

## Decisions

D-37 tags are a persistent per-user vocabulary created lazily · D-38 artifact
content stays API-only (D-24) while tags are user metadata editable from the web.

## Outcome

Shipped.

- `Tag(user, name, slug, created_at)` with unique `(user, slug)` and index
  `(user, name)`; `Artifact.tags` M2M; migration
  `artifacts/0002_tag_artifact_tags.py`; admin for `Tag`.
- `pullini/artifacts/services.py`: `normalize_tag` (trim/collapse/≤50), `TagError`,
  `validate_tags` (dedupe + cap 20), `resolve_tags` (lazy `get_or_create`,
  case-folded slug, first-writer display case), `set_artifact_tags`, `add_tags`,
  `remove_tags`, `delete_tag`, `tags_with_counts` (annotated `count`, includes
  orphans).
- REST (`pullini/artifacts/api.py`): `tags` in list/detail payloads (names ordered
  by name); create/PUT/PATCH accept `tags` (a present key replaces the set; PATCH
  may be tags-only); `GET /api/artifacts/?tag=<slug>`; `GET /api/tags/` and
  `DELETE /api/tags/<slug>/`; `parse_str_list` helper in `api/http.py`.
- Web: `tag_add`/`tag_remove` (`POST`, HTMX partial or redirect) and `tag_delete`
  (owner-scoped, redirects to the list); `?tag=` list filter validated against the
  vocabulary; `_tags.html` (editable chips + datalist on detail; read-only chips
  on list/shared) and `_tag_filter.html` (counts + inline delete).
- MCP (`mcp/src/pullini_mcp/`): `create_artifact`/`update_artifact` pass `tags`
  (tags-only updates allowed); `list_tags` and `delete_tag` client methods and
  tools; both `skill.md` files document tags.
- Tests: `tests/test_artifact_tags.py` (service + web), tag coverage in
  `tests/test_artifacts_api.py`, and MCP client/server tag tests.

Verification: `uv run pytest` → 230 passed, 1 skipped; `mcp` `uv run pytest` →
31 passed; `ruff check`/`format --check` clean (root and `mcp`); `manage.py check`
and `makemigrations --check` clean.
