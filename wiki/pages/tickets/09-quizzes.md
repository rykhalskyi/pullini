---
created: 2026-10-12
type: ticket
status: implemented
summary: T9 — quizzes core: Quiz/Question models, validation/scoring services and the read-only web surface (take, score, badges).
---

# T9 — Quizzes (core: model, services, web)

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Extends the [T4 — Artifacts](04-artifacts.md) model and the wiki `Page` model
(raw input: [03-quiz.md](../../raw/03-quiz.md)). The [T10 — Quizzes REST API](10-quizzes-api.md)
and [T11 — Quizzes MCP tools](11-quizzes-mcp.md) build on this.

## Spec

Readers want to test their understanding of a wiki page or an artifact. An agent
generates a short quiz about the page's topic (through the API/MCP in T10/T11) and
a reader answers it in the web UI for a score. This ticket delivers the **domain
and web surface only**; it does not add API or MCP tools.

Locked decisions:

- A quiz targets **exactly one** `Page` *or* one `Artifact`, modelled as two
  nullable FKs plus a discriminator. There is **one quiz per (user, page)** and per
  (user, artifact); re-running the generator **replaces** it (upsert).
- Quizzes are **private to their owner**. Deleting the source page/artifact
  **cascades** to the quiz (D-39).
- Each quiz stores the source's `content_hash` at generation so the UI can flag a
  quiz that is **stale** after a Git re-sync (D-41).
- Up to **10** multiple-choice questions, one correct option each. Correctness is
  stored server-side; the quiz row keeps `last_score` / `best_score` for the score
  badge. No attempts table (D-40).

Web surface:

- A quiz **button** next to the favorite star on the wiki page
  (`templates/wiki/page.html`) and at the top of an artifact
  (`templates/artifacts/detail.html`), showing the current score badge when a quiz
  exists.
- A "Quizzes" section on `templates/projects/project_detail.html` listing the
  user's quizzes for that project's pages.
- A quiz page (`templates/quizzes/detail.html`) where the owner answers questions,
  submits, and sees the score; retake is allowed.

Out of scope: REST API (T10), MCP tools and skill (T11), multi-select / true-false
/ free-text questions, user question reordering, sharing/unlisted quiz links,
leaderboards, tags on quizzes, scheduled regeneration, cross-user or
project-visible quizzes.

## Plan

1. New app `src/pullini/quizzes/` (`apps.py`, `models.py`, `services.py`,
   `views.py`, `urls.py`), added to `INSTALLED_APPS` and the root URL config.
2. Models + migration: `Quiz(user, page?, artifact?, target_type, source_hash,
   last_score, best_score, created_at, updated_at)` with unique `(user, page)`,
   unique `(user, artifact)` and a check constraint that exactly one target is set;
   `Question(quiz, position, text, options, correct_index, explanation?)`, unique
   `(quiz, position)`. Cascade from `Page`/`Artifact`; register in admin.
3. Services: `validate_questions` (1–10 questions, 2–6 options, one in-range
   `correct_index`, non-empty text, length caps), `create_quiz` (upsert keyed on
   owner + target, recomputes and stores `source_hash`), `delete_quiz`,
   `score_submission`, `list_quizzes`; `get_quiz_for(user, page|artifact)`.
4. Web: `quiz_take` (GET) and `quiz_submit` (POST, owner-scoped) views + URLs;
   templates `templates/quizzes/detail.html` and a `_score_badge.html` partial;
   quiz button on the wiki page and artifact detail; "Quizzes" section on the
   project page.
5. Tests: `tests/test_quizzes.py` (models, validation, scoring, web take/submit,
   badges, staleness flag, cascade).
6. Wiki: this ticket; link from E6.

## Decisions

D-39 private per-user quizzes, one per (user, target), nullable FK + discriminator,
cascade + upsert · D-40 correctness server-side with last/best score on the quiz
(self-study) · D-41 quiz stores the source `content_hash` for staleness.

## Outcome

Shipped.

- New app `pullini/quizzes/`: `Quiz(user, page?, artifact?, target_type,
  source_hash, last_score, best_score, created/updated)` with unique
  `(user, page)`, unique `(user, artifact)` and a `quiz_exactly_one_target` check
  constraint; `Question(quiz, position, text, options, correct_index,
  explanation)` unique per `(quiz, position)`; migration `0001_initial`; admin
  registration with a question inline.
- `services.py`: `QuizError`, `validate_questions` (1–10 questions, 2–6 options,
  in-range `correct_index`, length caps), `create_quiz` (upsert keyed on owner +
  target, captures `content_hash`), `get_quiz`, `list_quizzes`,
  `quizzes_for_project`, `delete_quiz`, `score_submission` (updates last/best).
- Web: `quizzes:detail` (take) and `quizzes:submit` (score) — login-gated and
  owner-scoped; `templates/quizzes/detail.html` and `_quiz_button.html` (score
  badge, "No quiz yet" hint); the button is wired next to the favorite star on
  `wiki/page.html` and at the top of `artifacts/detail.html`; a "Quizzes" section
  lists the user's page quizzes on `project_detail.html`; `is_stale` flags a quiz
  whose source changed.
- Tests: `tests/test_quizzes.py` (27 tests: constraints, validation, replace,
  scoping, cascade, staleness, scoring, web take/submit, badges, project list).

Verification: `uv run pytest` → 270 passed, 3 skipped; `ruff check`/`format
--check` clean; `manage.py check` and `makemigrations --check` clean.
