"""Settings hardening tests.

These run settings import in a subprocess so module-level guards are re-evaluated.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

_BASE_ENV = {
    "DJANGO_SETTINGS_MODULE": "pullini.settings",
    "PYTHONPATH": str(SRC),
    "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "localhost",
}


def _run(code: str, **overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(_BASE_ENV)
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def _load(expr: str, **overrides: str) -> subprocess.CompletedProcess[str]:
    return _run(
        f"import django; django.setup(); from django.conf import settings; print({expr})",
        **overrides,
    )


def test_weak_secret_is_rejected_in_production():
    result = _load("settings.SECRET_KEY", DJANGO_SECRET_KEY="change-me-in-production")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_short_secret_is_rejected_in_production():
    result = _load("settings.SECRET_KEY", DJANGO_SECRET_KEY="short")

    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY" in result.stderr


def test_strong_secret_is_accepted():
    key = "x" * 48

    result = _load("settings.SECRET_KEY", DJANGO_SECRET_KEY=key)

    assert result.returncode == 0, result.stderr
    assert key in result.stdout


def test_proxy_header_not_trusted_by_default():
    result = _load(
        "settings.SECURE_PROXY_SSL_HEADER is None",
        DJANGO_SECRET_KEY="x" * 48,
    )

    assert result.returncode == 0, result.stderr
    assert "True" in result.stdout


def test_proxy_header_trusted_when_opted_in():
    result = _load(
        "settings.SECURE_PROXY_SSL_HEADER",
        DJANGO_SECRET_KEY="x" * 48,
        DJANGO_TRUST_PROXY_HEADERS="true",
    )

    assert result.returncode == 0, result.stderr
    assert "HTTP_X_FORWARDED_PROTO" in result.stdout
