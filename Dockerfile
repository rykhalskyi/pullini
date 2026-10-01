# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 — build front-end assets (Tailwind CSS)
# ---------------------------------------------------------------------------
FROM node:24-alpine AS assets

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY assets ./assets
COPY templates ./templates
COPY src ./src
RUN npm run build:css

# ---------------------------------------------------------------------------
# Stage 2 — uv binary
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:0.12.15 AS uv

# ---------------------------------------------------------------------------
# Stage 3 — runtime
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS runtime

# Build metadata, surfaced at /healthz (staff) so you can tell which commit is
# running. Pass it in CI: --build-arg PULLINI_GIT_SHA=<git sha>.
ARG PULLINI_GIT_SHA=""

LABEL org.opencontainers.image.title="pullini" \
      org.opencontainers.image.source="https://github.com/rykhalskyi/pullini" \
      org.opencontainers.image.revision="${PULLINI_GIT_SHA}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PULLINI_GIT_SHA="${PULLINI_GIT_SHA}"

# git is required for project synchronization (E3) and the health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .
COPY --from=assets /app/static/css/app.css ./static/css/app.css
RUN uv sync --frozen --no-dev

RUN mkdir -p /data \
    && useradd --system --uid 10001 --home-dir /app pullini \
    && chown -R pullini:pullini /app /data

USER pullini

# Configuration is environment-driven; sane production defaults live here.
ENV DJANGO_DEBUG=false \
    DATA_DIR=/data \
    DJANGO_ALLOWED_HOSTS=localhost

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["gunicorn", "pullini.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
