"""Verify the database layer is engine-agnostic (SQLite default, PostgreSQL via URL)."""

from __future__ import annotations

import environ
from django.db.utils import load_backend


def test_configured_engine_is_supported():
    from django.conf import settings

    assert settings.DATABASES["default"]["ENGINE"] in {
        "django.db.backends.sqlite3",
        "django.db.backends.postgresql",
    }


def test_postgres_url_selects_installed_driver():
    config = environ.Env().db_url_config("postgres://user:pass@db:5432/pullini")

    assert config["ENGINE"] == "django.db.backends.postgresql"
    # Importing the backend proves psycopg is installed and loadable.
    backend = load_backend(config["ENGINE"])
    assert backend.Database is not None
