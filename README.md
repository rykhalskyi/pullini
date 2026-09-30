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

Set a real `DJANGO_SECRET_KEY` (at least 32 random characters) in `.env` first —
Compose runs with `DJANGO_DEBUG=false`, and the placeholder from
`.env.example` is refused in production:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"   # paste into .env
docker compose up --build
```

SQLite and data live in the `pullini-data` volume (`/data`). Change the published
host port with `PULLINI_PORT` (default `8000`) if it is already in use:

```bash
PULLINI_PORT=8080 docker compose up --build
```

For PostgreSQL, set
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

Production TLS is opt-in: set `DJANGO_TRUST_PROXY_HEADERS=true` only when a proxy
you control strips `X-Forwarded-Proto`, and optionally `DJANGO_SECURE_SSL_REDIRECT`
and `DJANGO_SECURE_HSTS_SECONDS`. Liveness is at `/livez` (process only);
`/healthz` reports dependency status and redacts details for anonymous users.
