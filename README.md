# Pullini

**A read-only Git-backed wiki browser.**

> Git is the source of truth. Pullini makes Git-based documentation easy to browse and search.

Wiki content is never edited in Pullini.

## Status

V1 feature-complete. Pullini provides:

- **Projects** — Git repository, branch, docs folder and update interval managed
  in the Django admin; public read-only list and detail pages.
- **Git synchronization** — shallow per-project clones, scheduled and manual
  refresh, per-project sync state, resilient to failures.
- **Wiki generation** — Markdown in the configured docs folder rendered as
  read-only pages with tree and recent navigation.
- **Search** — project-scoped and global search with contextual snippets, backed
  by PostgreSQL full-text search or portable ORM matching on SQLite.

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

Then open http://localhost:8000 — status is at `/healthz`, and projects are added
in the Django admin at `/admin/`.

## Syncing and generating pages

Wiki pages are regenerated automatically when a sync detects a changed commit.
To sync or rebuild manually:

```bash
uv run python manage.py sync_projects            # sync projects whose interval has elapsed
uv run python manage.py sync_projects --force    # sync all enabled projects now
uv run python manage.py sync_projects --project <slug>
uv run python manage.py generate_pages           # regenerate pages from local clones
uv run python manage.py generate_pages --project <slug>
```

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

For PostgreSQL, set `DATABASE_URL` in `.env` and start the `postgres` profile:

```bash
docker compose --profile postgres up --build
```

### Kubernetes / k3s + FluxCD

Manifests live in [`k8s/`](k8s/). Create the Secret from
[`k8s/secret.example.yaml`](k8s/secret.example.yaml) with your secret tooling,
then apply via Flux (`k8s/flux.yaml`) or `kubectl apply -k k8s`.

The entrypoint applies migrations, collects static files, and then seeds the
single admin user when `DJANGO_SUPERUSER_PASSWORD` is present. Put
`DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and
`DJANGO_SUPERUSER_PASSWORD` in the Secret and the first boot creates the admin
user if it does not exist yet (an existing user is left untouched). To rotate
the password later, update the Secret and run
`python manage.py changepassword <user>` in the container, or delete the user
and restart.

The container image is built on demand by the
[`Build image`](.github/workflows/build-image.yml) workflow (Actions → **Build
image** → **Run workflow**). It pushes
`ghcr.io/rykhalskyi/pullini:sha-<commit>` (plus `latest` and an optional extra
tag) and stamps the commit into the image. Run `/healthz` as staff to see the
running `version` and `revision`.

## Configuration

All configuration is environment-driven; see [`.env.example`](.env.example).
Key variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
`DATABASE_URL`, `DATA_DIR`.

Production TLS is opt-in: set `DJANGO_TRUST_PROXY_HEADERS=true` only when a proxy
you control strips `X-Forwarded-Proto`, and optionally `DJANGO_SECURE_SSL_REDIRECT`
and `DJANGO_SECURE_HSTS_SECONDS`. Liveness is at `/livez` (process only);
`/healthz` reports dependency status and redacts details for anonymous users.
