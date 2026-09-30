---
created: 2026-09-30
type: build-deploy
status: implemented
summary: Build, test, lint and deploy commands for Pullini (uv, Tailwind, Docker Compose, k3s/FluxCD).
---

# Build & Deploy

## Requirements

uv (Python 3.14), Node.js 24 (Tailwind), git, Docker (for containers).

## Local development

```bash
cp .env.example .env
uv sync
npm install
npm run build:css          # or: npm run watch:css
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Health: `GET /healthz`. Config is environment-driven; see [`.env.example`](../../.env.example)
(`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `DATA_DIR`).

## Test & lint

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Deployment

See [V1 HLD §3 Installation types](specs/pullini-v1-hld.md#3-installation-types).

### Docker Compose

```bash
docker compose up --build                      # SQLite, data in the pullini-data volume
docker compose --profile postgres up --build   # PostgreSQL (set DATABASE_URL in .env)
```

The entrypoint runs migrations (with retries) and `collectstatic` before gunicorn.

### Kubernetes / k3s + FluxCD

Manifests in [`k8s/`](../../k8s). Create the Secret from `k8s/secret.example.yaml`
with your secret tooling, then apply via Flux (`k8s/flux.yaml`) or `kubectl apply -k k8s`.

## Persistence

Everything mutable lives under `DATA_DIR` (`/data` in containers):

```text
/data
├── database      # SQLite (when used)
└── repositories  # local Git clones (E3)
```
