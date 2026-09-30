# Pullini

**A read-only Git-backed wiki browser.**

> Git is the source of truth. Pullini makes Git-based documentation easy to browse and search.

Wiki content is never edited in Pullini.

## Status

Early V1 — foundation only. The application currently provides a bootable Django
monolith with configuration, persistence, deployment manifests and a health
endpoint. Projects, Git synchronization, wiki generation and search land in later
epics.

See the design: [`wiki/pages/specs/pullini-v1-hld.md`](wiki/pages/specs/pullini-v1-hld.md).

## Stack

Python 3.14 · Django 6 · Django Templates + HTMX · Tailwind CSS · SQLite (default)
or PostgreSQL · Git CLI · database-native full-text search.

## Local development

Requires [uv](https://docs.astral.sh/uv/) and Node.js (for Tailwind).

```bash
cp .env.example .env
uv sync
npm install
npm run build:css          # or: npm run watch:css
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

Then open http://localhost:8000 — status is at `/healthz`.

## Tests and lint

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## Deployment

### Docker Compose

```bash
docker compose up --build
```

SQLite and data live in the `pullini-data` volume (`/data`). For PostgreSQL, set
`DATABASE_URL` in `.env` and start the `postgres` profile:

```bash
docker compose --profile postgres up --build
```

### Kubernetes / k3s + FluxCD

Manifests live in [`k8s/`](k8s/). Create the Secret from
[`k8s/secret.example.yaml`](k8s/secret.example.yaml) with your secret tooling,
then apply via Flux (`k8s/flux.yaml`) or `kubectl apply -k k8s`.

## Configuration

All configuration is environment-driven; see [`.env.example`](.env.example).
Key variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
`DATABASE_URL`, `DATA_DIR`.
