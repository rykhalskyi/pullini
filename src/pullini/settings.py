"""Django settings for Pullini.

Configuration is environment-driven (12-factor) so the very same image can run
on Docker Compose (SQLite) and on Kubernetes/k3s (PostgreSQL). The application
never depends on the installation type; only configuration differs.
"""

from __future__ import annotations

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

from pullini import __version__

# repo root: <root>/src/pullini/settings.py -> parents[2]
BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_SECRET_KEY=(str, "insecure-development-key-change-me"),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "[::1]"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    DJANGO_SECURE_COOKIES=(bool, True),
    DJANGO_TRUST_PROXY_HEADERS=(bool, False),
    DJANGO_SECURE_SSL_REDIRECT=(bool, False),
    DJANGO_SECURE_HSTS_SECONDS=(int, 0),
    DATA_DIR=(str, str(BASE_DIR / "data")),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS")

# Values shipped in examples/manifests must never sign anything in production.
_INSECURE_SECRET_KEYS = {
    "insecure-development-key-change-me",
    "change-me-in-production",
    "change-me",
    "dev-only-insecure-secret",
    "replace-with-a-long-random-value",
    "secret",
}

if not DEBUG and (SECRET_KEY in _INSECURE_SECRET_KEYS or len(SECRET_KEY) < 32):
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a unique, random value of at least 32 "
        "characters when DEBUG is off."
    )

# ---------------------------------------------------------------------------
# Persistence layout. Everything mutable lives under DATA_DIR so it can be a
# single mounted volume in Docker Compose (/data) or a PersistentVolume in k8s.
# ---------------------------------------------------------------------------
DATA_DIR = Path(env("DATA_DIR")).resolve()
DATABASE_DIR = DATA_DIR / "database"
REPOSITORIES_DIR = DATA_DIR / "repositories"

# ---------------------------------------------------------------------------
# Build metadata. APP_VERSION comes from the package; GIT_REVISION is baked in
# at image build time (Dockerfile ARG -> PULLINI_GIT_SHA). Reported by /healthz.
# ---------------------------------------------------------------------------
APP_VERSION = __version__
GIT_REVISION = env("PULLINI_GIT_SHA", default="")

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "pullini.core",
    "pullini.projects",
    "pullini.wiki",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "pullini.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "pullini.wsgi.application"
ASGI_APPLICATION = "pullini.asgi.application"

# ---------------------------------------------------------------------------
# Database. SQLite by default (self-contained Compose install); PostgreSQL via
# a DATABASE_URL (k3s/production). Kept engine-agnostic for E5 full-text search.
# ---------------------------------------------------------------------------
DATABASE_URL = env("DATABASE_URL", default="") or f"sqlite:///{DATABASE_DIR / 'db.sqlite3'}"
DATABASES = {"default": env.db_url_config(DATABASE_URL)}
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault("timeout", 20)

LOGIN_URL = "/admin/login/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# I18N
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# ---------------------------------------------------------------------------
# Security (production only)
# ---------------------------------------------------------------------------
if not DEBUG:
    # Only trust X-Forwarded-Proto when an operator confirms a proxy strips it.
    # Trusting it unconditionally lets any direct client spoof HTTPS.
    if env("DJANGO_TRUST_PROXY_HEADERS"):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    SECURE_COOKIES = env("DJANGO_SECURE_COOKIES")
    SESSION_COOKIE_SECURE = SECURE_COOKIES
    CSRF_COOKIE_SECURE = SECURE_COOKIES
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"

    # Off by default so a misconfigured proxy cannot cause redirect loops;
    # enable alongside DJANGO_TRUST_PROXY_HEADERS when TLS terminates upstream.
    SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT")

    SECURE_HSTS_SECONDS = env("DJANGO_SECURE_HSTS_SECONDS")
    if SECURE_HSTS_SECONDS:
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
}
