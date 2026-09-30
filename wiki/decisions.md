# Decisions

Append-only decision record. The "why" lives here; the full change history lives in git.

- [2026-09-30] D-01 — Git is the source of truth, the database is not the canonical wiki content store — because Pullini only generates presentation and must never diverge from repository content
- [2026-09-30] D-02 — One Python/Django monolith, no microservices — because V1 must stay small and operationally simple
- [2026-09-30] D-03 — Single Admin role; wiki pages are public and read-only, content cannot be edited in Pullini — because the wiki is generated from Git
- [2026-09-30] D-04 — SQLite as the default (Docker Compose) with PostgreSQL optional for k3s/production — because it keeps Compose self-contained without losing production support
- [2026-09-30] D-05 — Automatic project sync every 10 minutes by default, plus manual Refresh now — because docs stay fresh without admin effort while allowing on-demand updates
- [2026-09-30] D-06 — Database-native full-text search (SQLite FTS5 / PostgreSQL FTS) instead of Elasticsearch/OpenSearch — because V1 avoids extra infrastructure, behind an abstraction layer
- [2026-09-30] D-07 — Each project keeps a persistent local clone treated as working-state/cache; Git history is neither required nor exposed — because only repo+branch+folder matter for wiki generation
- [2026-09-30] D-08 — Single env-driven Django settings module (no base/dev/prod split) — because install types differ by configuration, not code
- [2026-09-30] D-09 — gunicorn/WSGI for production; ASGI present but unused — because the HTMX UI is server-rendered request/response
- [2026-09-30] D-10 — Tailwind CSS v4 via npm CLI with design tokens declared in @theme — because the HLD mandates Tailwind and tokens centralize the design guidelines
- [2026-09-30] D-11 — Scheduled sync via a management command plus external cron/CronJob, not Celery or django-q2 — because V1 avoids unnecessary infrastructure
- [2026-09-30] D-12 — Project management uses Django's built-in admin rather than a custom admin UI — because it is secure and fast, while public wiki pages stay custom and read-only
- [2026-09-30] D-13 — Public project URLs are slug-based and repo URLs accept https/ssh/scp-like Git forms — because ssh remotes are common and friendly URLs suit documentation
- [2026-09-30] D-14 — Git access uses the CLI via subprocess rather than GitPython/pygit2 — because Pullini only needs a shallow working tree and the stdlib keeps dependencies minimal
- [2026-09-30] D-15 — The scheduler runs as a loop in a secondary container/sidecar rather than a CronJob — because the clone lives on a ReadWriteOnce volume that only one pod can mount, and the sidecar shares the pod volume
- [2026-09-30] D-16 — Each project's sync is serialized with a per-project flock file — because manual refresh and the scheduled run can execute concurrently
- [2026-09-30] D-17 — Markdown rendering uses Python-Markdown with core extensions and hand-written content styles, not the Tailwind typography plugin — because it keeps dependencies lean and preserves the navy/white reading aesthetic
- [2026-09-30] D-18 — Pages are stored in the database as derived metadata plus rendered HTML and are fully regenerable from the clone; Git stays canonical and regeneration is keyed on a content hash
- [2026-09-30] D-19 — Page URLs use the source path without extension under /projects/<slug>/wiki/, reserving index/ recent/ assets/, and relative .md links and asset src are rewritten to internal routes
- [2026-09-30] D-20 — Dark mode is a class on <html> that overrides CSS-variable design tokens (surface/panel/code-bg/ink/...), toggled by a header button persisted in localStorage — because component markup stays token-based and both themes share one stylesheet
- [2026-09-30] D-21 — Search is abstracted behind a backend interface: PostgreSQL uses native full-text (SearchVector/SearchRank), SQLite uses portable ORM matching — because V1 avoids extra infrastructure and the interface leaves room to add SQLite FTS5 later
- [2026-09-30] D-22 — The derived Page table is the search index, regenerated when project content changes — because it is always current and needs no separate index store or service
