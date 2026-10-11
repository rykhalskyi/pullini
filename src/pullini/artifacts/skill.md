---
name: pullini-artifacts
description: Create, read, update, delete and share Pullini artifacts over the authenticated REST API. Use when an agent needs to persist AI-generated Markdown notes, reports or diagrams to a Pullini host.
---

# Pullini Artifacts

Pullini artifacts are user-owned Markdown documents that Pullini renders
read-only (Markdown, tables, code and Mermaid diagrams). You write them as an
agent through the REST API; the web UI is a view onto what you wrote.

## Authentication

Every request needs a personal access token (PAT) as a bearer header:

```http
Authorization: Bearer pln_xxxxxxxx_yyyyyyyyyyyyyyyyyyyyyyyy
```

All resources are scoped to the token's owner. Requests without a valid token
get `401`.

## Endpoints

```text
GET    /api/me/                      who the token belongs to
GET    /api/artifacts/               list your artifacts
POST   /api/artifacts/               create an artifact
GET    /api/artifacts/<slug>/        fetch one artifact (source + rendered HTML)
PUT    /api/artifacts/<slug>/        replace title and content
PATCH  /api/artifacts/<slug>/        update title and/or content
DELETE /api/artifacts/<slug>/        delete an artifact
POST   /api/artifacts/<slug>/share/  enable the unlisted share link
DELETE /api/artifacts/<slug>/share/  revoke the share link
```

## Create

`POST /api/artifacts/` with a JSON body:

```json
{
  "title": "Weekly Report",
  "content": "# Weekly Report\n\nAll good.",
  "visibility": "private"
}
```

- `title` (string, required)
- `content` (string, required; Markdown source)
- `visibility` (`"private"` or `"unlisted"`, optional; default `"private"`)
  - `"unlisted"` creates the artifact with an active share link.

Returns `201` with the artifact detail:

```json
{
  "slug": "weekly-report",
  "title": "Weekly Report",
  "visibility": "private",
  "share_url": null,
  "content": "# Weekly Report\n\nAll good.",
  "html": "<h1 id=\"weekly-report\">Weekly Report</h1>\n<p>All good.</p>",
  "plain_text": "Weekly Report All good.",
  "created_at": "2026-10-11T12:00:00+00:00",
  "updated_at": "2026-10-11T12:00:00+00:00"
}
```

The `slug` is derived from the title, unique per user, and **frozen at
creation**: renaming later keeps the same slug, so URLs and API addresses stay
stable.

## Read

- `GET /api/artifacts/` returns `{"artifacts": [...]}` of list items
  (`slug`, `title`, `visibility`, `share_url`, timestamps).
- `GET /api/artifacts/<slug>/` returns the full detail shown above.

List results are capped (no pagination).

## Update

- `PUT /api/artifacts/<slug>/` replaces both fields: `{"title": ..., "content": ...}`.
- `PATCH /api/artifacts/<slug>/` updates only what you send (`title` and/or
  `content`).

Updating `content` re-renders `html` and `plain_text`.

## Delete

`DELETE /api/artifacts/<slug>/` removes the artifact and returns `204`.

## Share

- `POST /api/artifacts/<slug>/share/` marks the artifact unlisted and returns the
  detail with a `share_url` such as `https://host/a/<token>/`. Anyone with the
  link can read it; no token is needed on that page.
- `DELETE /api/artifacts/<slug>/share/` revokes the link and returns `204`.

## Authoring notes

- `content` is Markdown. Fenced blocks tagged `mermaid` render as diagrams.
- Raw HTML is sanitized; scripts and event handlers are stripped.
- Keep `title` short; put structure in the Markdown headings.

## Errors

Failures return a JSON body and an HTTP status:

```json
{"error": "invalid_field", "detail": "\"title\" must be a non-empty string."}
```

Common errors: `401` (missing/invalid/expired/revoked token), `400`
(`invalid_json`, `invalid_field`), `404` (unknown slug or another user's
artifact), `405` (method not allowed).
