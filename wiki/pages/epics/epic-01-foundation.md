---
created: 2026-09-30
type: epic
status: implemented
summary: E1 — bootable/deployable Django monolith: env-driven config, SQLite/Postgres, /data persistence, health, Docker, k8s, CI.
---

# E1 — Foundation & Deployment

Design: [Pullini V1 — High-Level Design](../specs/pullini-v1-hld.md) (§2, §3, §14, §15).

## Spec

Deliver an empty-but-real application: a bootable Django monolith that connects to a
database, persists data under a single mount point, renders a styled page, reports
health, and ships to both Docker Compose and Kubernetes. It must not depend on the
installation type (HLD §3), and a failing subsystem must never take the app down
(HLD §15).

Explicitly out of scope: projects/auth UI (E2), Git sync (E3), Markdown (E4),
search (E5), full navigation (E6).

## Plan

1. Tooling: uv deps, ruff/pytest config, `.env.example`, `.gitignore`, README.
2. Django scaffold: `manage.py`, env-driven settings, urls, wsgi/asgi.
3. `pullini.core` app: startup dir creation, health checks, views.
4. DB abstraction: SQLite default, PostgreSQL via `DATABASE_URL`.
5. Persistence layout: `DATA_DIR/{database,repositories}`.
6. Templates + Tailwind v4 design tokens from the design guidelines.
7. Docker (multi-stage, non-root, git), entrypoint, Compose (+ postgres profile).
8. k8s/FluxCD manifests incl. a suspended sync CronJob.
9. Tests + CI (sqlite **and** postgres).

## Outcome

Shipped. Verification: `uv run pytest` (7 passed), `uv run ruff check` clean,
`docker compose config` valid, `kubectl kustomize k8s` valid, `GET /healthz` → 200.

Key files:

- Config: [`src/pullini/settings.py`](../../../src/pullini/settings.py),
  [`src/pullini/core/health.py`](../../../src/pullini/core/health.py)
- Packaging: [`pyproject.toml`](../../../pyproject.toml)
- Deploy: [`Dockerfile`](../../../Dockerfile), [`docker-compose.yml`](../../../docker-compose.yml),
  [`k8s/`](../../../k8s), [`.github/workflows/ci.yml`](../../../.github/workflows/ci.yml)
- Front end: [`templates/base.html`](../../../templates/base.html),
  [`assets/css/input.css`](../../../assets/css/input.css)

Deviations: the uv `src/` layout was kept and the generated `pullini` console script
was removed. Django's project package lives at `src/pullini` with a **single**
env-driven settings module rather than a `base/dev/prod` split (see D-08).

## Decisions

D-08 config/settings layout · D-09 WSGI/gunicorn · D-10 Tailwind tokens ·
D-11 scheduler via external cron/CronJob. See [`decisions.md`](../../decisions.md).

## Next

E2 — Admin & Projects.
