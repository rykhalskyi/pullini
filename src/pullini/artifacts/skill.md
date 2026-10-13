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
PUT    /api/artifacts/<slug>/        replace title and content (tags optional)
PATCH  /api/artifacts/<slug>/        update title, content and/or tags
DELETE /api/artifacts/<slug>/        delete an artifact
POST   /api/artifacts/<slug>/share/  enable the unlisted share link
DELETE /api/artifacts/<slug>/share/  revoke the share link
GET    /api/tags/                    list your tags with artifact counts
DELETE /api/tags/<slug>/             delete a tag from your vocabulary
GET    /api/pages/                   list readable wiki pages (?project=<slug>)
GET    /api/pages/<project>/<path>/  fetch a wiki page's source Markdown
GET    /api/quizzes/                 list your quizzes
POST   /api/quizzes/                 create or replace a quiz
GET    /api/quizzes/<id>/            fetch one quiz (questions + your scores)
DELETE /api/quizzes/<id>/            delete a quiz
POST   /api/quizzes/<id>/attempts/   submit answers, get the score
```

## Create

`POST /api/artifacts/` with a JSON body:

```json
{
  "title": "Weekly Report",
  "content": "# Weekly Report\n\nAll good.",
  "visibility": "private",
  "tags": ["reports", "weekly"]
}
```

- `title` (string, required)
- `content` (string, required; Markdown source)
- `visibility` (`"private"` or `"unlisted"`, optional; default `"private"`)
  - `"unlisted"` creates the artifact with an active share link.
- `tags` (list of strings, optional; default `[]`). Each name is trimmed and
  capped at 50 characters; at most 20 tags per artifact. Tags are created in
  your per-user vocabulary on first use.

Returns `201` with the artifact detail:

```json
{
  "slug": "weekly-report",
  "title": "Weekly Report",
  "visibility": "private",
  "share_url": null,
  "tags": ["reports", "weekly"],
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
  (`slug`, `title`, `visibility`, `share_url`, `tags`, timestamps).
- `GET /api/artifacts/<slug>/` returns the full detail shown above.
- `GET /api/artifacts/?tag=<slug>` filters to one tag of your vocabulary.

List results are capped (no pagination).

## Update

- `PUT /api/artifacts/<slug>/` replaces title and content:
  `{"title": ..., "content": ...}`. An optional `tags` key replaces the tag set;
  omitted, tags stay unchanged.
- `PATCH /api/artifacts/<slug>/` updates only what you send (`title`, `content`
  and/or `tags`); a `tags`-only body is valid.

Updating `content` re-renders `html` and `plain_text`. Sending `tags` replaces
the whole set (use `[]` to clear it).

## Tags

- `GET /api/tags/` returns `{"tags": [{"name", "slug", "count"}]}` — your
  persistent vocabulary, including tags with `count` `0`.
- `DELETE /api/tags/<slug>/` deletes a tag everywhere and returns `204`. The
  `slug` is the case-folded form of the name (e.g. `Weekly Report` →
  `weekly-report`).

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

## Pages & quizzes

A quiz is a private, self-study multiple-choice quiz about exactly one wiki page
or one artifact. Read the source first, then create the quiz.

- `GET /api/pages/?project=<slug>` lists readable pages; `GET
  /api/pages/<project>/<path>/` returns one page's source `content` (use it to
  write grounded questions).
- `POST /api/quizzes/` targets exactly one source and takes a `questions` list:

  ```json
  {
    "page": {"project": "payments", "path": "guide/setup.md"},
    "questions": [
      {"text": "What port?", "options": ["80", "443"], "correct_index": 1,
       "explanation": "TLS is on 443."}
    ]
  }
  ```

  Or target an artifact with `{"artifact": "<slug>", "questions": [...]}`.
  Up to 10 questions; each needs 2–6 `options` and an in-range `correct_index`
  (an optional `explanation`). Creating again for the same target **replaces**
  it (`200`), a first create returns `201`.
- `POST /api/quizzes/<id>/attempts/` with `{"answers": [1, 0, ...]}` scores your
  answers and returns `score`, `total`, `last_score`, `best_score` and per-question
  correctness.

## Errors

Failures return a JSON body and an HTTP status:

```json
{"error": "invalid_field", "detail": "\"title\" must be a non-empty string."}
```

Common errors: `401` (missing/invalid/expired/revoked token), `400`
(`invalid_json`, `invalid_field`), `404` (unknown slug or another user's
artifact), `405` (method not allowed).
