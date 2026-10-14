---
created: 2026-10-13
type: ticket
status: implemented
summary: T12 — Q&A core: QandA/QandAItem models, validation/upsert services and the read-only static FAQ web surface for a wiki page or artifact.
---

# T12 — Q&A (core: model, services, web)

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Mirrors [T9 — Quizzes (core)](09-quizzes.md) and extends the [T4 — Artifacts](04-artifacts.md)
model and the wiki `Page` model. The [T13 — Q&A REST API](13-qanda-api.md) and
[T14 — Q&A MCP tools](14-qanda-mcp.md) build on this.

## Spec

Readers want a study/reference sheet of agent-authored question-and-answer pairs
grounded in a wiki page or an artifact. Unlike a quiz, a Q&A page is a **static
FAQ**: every answer is visible, nothing is scored, and there is no runtime LLM.
An agent generates the Q&A through the API/MCP in T13/T14; this ticket delivers
the **domain and web surface only**; it does not add API or MCP tools.

Locked decisions:

- A Q&A set targets **exactly one** `Page` *or* one `Artifact`, modelled as two
  nullable FKs plus a discriminator. There is **one set per (user, page)** and per
  (user, artifact); re-running the generator **replaces** it (upsert). Sets are
  **private to their owner**; deleting the source page/artifact **cascades** to the
  set (D-43).
- A Q&A set is a **static, agent-authored FAQ**: all answers are visible, there is
  no scoring, no attempts table and no runtime model. Each answer is **Markdown**,
  rendered and sanitized at write time through the existing `pullini.wiki.markup`
  pipeline (like artifacts), so code blocks and links work (D-44).
- Each set stores the source's `content_hash` at generation so the UI can flag a
  set that is **stale** after a Git re-sync (D-45).
- Up to **50** question/answer pairs, ordered by author-supplied position.

Web surface:

- A **Q&A button** next to the quiz button on the wiki page
  (`templates/wiki/page.html`) and at the top of an artifact
  (`templates/artifacts/detail.html`), showing the pair count when a set exists
  and a copy-the-reference hint when it does not.
- A "Q&A" section on `templates/projects/project_detail.html` listing the user's
  Q&A sets for that project's pages.
- A Q&A page (`templates/qanda/detail.html`) rendering the questions with their
  answers, a stale banner, and a back-to-article link.

Out of scope: REST API (T13), MCP tools and skill (T14), scoring/attempts,
runtime answering, answer hiding/reveal, sharing or unlisted links, tags,
leaderboards, scheduled regeneration, cross-user or project-visible sets.

## Plan

1. New app `src/pullini/qanda/` (`apps.py`, `models.py`, `services.py`,
   `views.py`, `urls.py`, `admin.py`), added to `INSTALLED_APPS` and the root URL
   config.
2. Models + migration: `QandA(user, page?, artifact?, target_type, source_hash,
   created_at, updated_at)` with unique `(user, page)`, unique `(user, artifact)`
   and a `qanda_exactly_one_target` check constraint; `QandAItem(qanda, position,
   question, answer, answer_html)`, unique `(qanda, position)`. Cascade from
   `Page`/`Artifact`; register in admin with an item inline.
3. Services: `validate_entries` (1–50 entries, non-empty question ≤500 chars,
   non-empty answer ≤5000 chars, renders/sanitizes `answer_html`), `create_qanda`
   (upsert keyed on owner + target, recomputes and stores `source_hash`),
   `get_qanda`, `list_qanda`, `qanda_for_project`, `delete_qanda`; `QandAError`.
4. Web: `qanda_detail` (GET, login-gated, owner-scoped) view + URL; template
   `templates/qanda/detail.html` and `_qanda_button.html`; button wired on the
   wiki page and artifact detail; "Q&A" section on the project page; `is_stale`
   flag.
5. Tests: `tests/test_qanda.py` (constraints, validation, replace, scoping,
   cascade, staleness, Markdown rendering, web surfaces).
6. Wiki: this ticket; link from E6.

## Decisions

D-43 private per-user Q&A sets, one per (user, target), nullable FK +
discriminator, cascade + upsert (mirrors D-39) · D-44 a Q&A set is a static
agent-authored FAQ with Markdown answers rendered/sanitized at write time, no
scoring or runtime LLM · D-45 each set stores the source `content_hash` for
staleness (mirrors D-41).

## Outcome

Shipped.

- New app `pullini/qanda/`: `QandA(user, page?, artifact?, target_type,
  source_hash, created/updated)` with unique `(user, page)`, unique
  `(user, artifact)` and a `qanda_exactly_one_target` check constraint;
  `QandAItem(qanda, position, question, answer, answer_html)` unique per
  `(qanda, position)`; migration `0001_initial`; admin registration with an item
  inline.
- `services.py`: `QandAError`, `validate_entries` (1–50 entries, non-empty
  question ≤500 chars, non-empty Markdown answer ≤5000 chars, `answer_html`
  rendered/sanitized through `pullini.wiki.markup`), `create_qanda` (upsert keyed
  on owner + target, captures `content_hash`), `get_qanda`, `list_qanda`,
  `qanda_for_project`, `delete_qanda`.
- Web: `qanda:detail` (login-gated, owner-scoped); `templates/qanda/detail.html`
  and `_qanda_button.html` (pair count, "No Q&A yet" hint); the button is wired
  next to the quiz button on `wiki/page.html` and at the top of
  `artifacts/detail.html`; a "Q&A" section lists the user's page sets on
  `project_detail.html`; `is_stale` flags a set whose source changed; Mermaid
  answers load the diagram scripts.
- Tests: `tests/test_qanda.py` (30 tests: constraints, validation, replace,
  scoping, cascade, staleness, Markdown rendering/sanitization, Mermaid, web).

Verification: `uv run pytest` → 333 passed, 3 skipped; `ruff check`/`format
--check` clean; `manage.py check` and `makemigrations --check` clean.
