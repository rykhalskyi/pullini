"""Tests for the core health endpoint and checks."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from pullini.core import health

pytestmark = pytest.mark.django_db


def test_healthz_reports_healthy(client):
    response = client.get(reverse("healthz"))

    assert response.status_code == 200, response.json()
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["checks"]["database"]["ok"] is True
    assert payload["checks"]["git"]["ok"] is True
    assert payload["checks"]["data_dir"]["ok"] is True
    assert payload["projects"] == {"total": 0, "enabled": 0}
    assert payload["last_sync"] is None


def test_livez_reports_ok_without_dependency_checks(client):
    response = client.get(reverse("livez"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_redacts_details_for_anonymous(client, settings):
    settings.DEBUG = False

    payload = client.get(reverse("healthz")).json()

    assert payload["checks"]["data_dir"]["detail"] in {"ok", "unavailable"}


def test_healthz_shows_details_to_staff(client, settings):
    settings.DEBUG = False
    user = get_user_model().objects.create_user("admin", password="secret", is_staff=True)
    client.force_login(user)

    payload = client.get(reverse("healthz")).json()

    assert payload["checks"]["data_dir"]["detail"] == str(settings.DATA_DIR)


def test_home_renders_design_shell(client):
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert b"Pullini" in response.content
    assert b"css/app.css" in response.content


def test_home_has_theme_toggle(client):
    response = client.get(reverse("home"))

    assert b"data-theme-toggle" in response.content
    assert b"js/theme.js" in response.content


def test_database_check_isolates_errors(monkeypatch):
    class BoomCursor:
        def __enter__(self):
            raise RuntimeError("database down")

        def __exit__(self, *exc):
            return False

    class BoomConnection:
        def cursor(self):
            return BoomCursor()

    monkeypatch.setattr(health, "connection", BoomConnection())

    check = health.check_database()

    assert check.ok is False
    assert "database down" in check.detail


def test_git_check_handles_missing_binary(monkeypatch):
    monkeypatch.setattr(health.shutil, "which", lambda name: None)

    check = health.check_git()

    assert check.ok is False
    assert "not found" in check.detail


def test_data_dir_check_creates_directory(tmp_path, settings, monkeypatch):
    target = tmp_path / "nested" / "data"
    monkeypatch.setattr(settings, "DATA_DIR", target)

    check = health.check_data_dir()

    assert check.ok is True
    assert target.is_dir()
