"""Health and status checks exposed by the application (HLD §15).

A failing subsystem must never make the whole application unavailable, so each
check is isolated and reported independently rather than raising.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass

from django.conf import settings
from django.db import connection


@dataclass(frozen=True)
class Check:
    ok: bool
    detail: str

    def as_dict(self) -> dict[str, object]:
        return {"ok": self.ok, "detail": self.detail}


def ensure_data_dirs() -> None:
    """Create the persistent data layout if it does not exist yet (HLD §14)."""
    for path in (settings.DATA_DIR, settings.DATABASE_DIR, settings.REPOSITORIES_DIR):
        path.mkdir(parents=True, exist_ok=True)


def check_database() -> Check:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # noqa: BLE001 - report any driver error as unhealthy
        return Check(False, f"{type(exc).__name__}: {exc}")
    return Check(True, connection.vendor)


def check_git() -> Check:
    path = shutil.which("git")
    if not path:
        return Check(False, "git binary not found on PATH")
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Check(False, f"{type(exc).__name__}: {exc}")
    return Check(True, result.stdout.strip())


def check_data_dir() -> Check:
    try:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not os.access(settings.DATA_DIR, os.W_OK):
            return Check(False, f"{settings.DATA_DIR} is not writable")
    except OSError as exc:
        return Check(False, f"{type(exc).__name__}: {exc}")
    return Check(True, str(settings.DATA_DIR))


def collect_status(*, detailed: bool = True) -> dict[str, object]:
    """Aggregate application status. Individual checks never raise.

    When ``detailed`` is false the per-check payloads are redacted so public
    status endpoints do not leak filesystem paths, versions or driver errors.
    """
    checks = {
        "database": check_database(),
        "git": check_git(),
        "data_dir": check_data_dir(),
    }
    healthy = all(check.ok for check in checks.values())
    if detailed:
        payload = {name: check.as_dict() for name, check in checks.items()}
    else:
        payload = {
            name: {"ok": check.ok, "detail": "ok" if check.ok else "unavailable"}
            for name, check in checks.items()
        }
    result = {
        "status": "healthy" if healthy else "unhealthy",
        "checks": payload,
        "projects": _project_counts(),
        "last_sync": _last_sync(),
    }
    if detailed:
        # Build identity, only for staff: which app version + commit is running.
        result["version"] = settings.APP_VERSION
        result["revision"] = settings.GIT_REVISION or None
    return result


def _last_sync() -> str | None:
    """ISO timestamp of the most recent successful project sync, if any."""
    try:
        from pullini.projects.models import ProjectSyncState

        value = (
            ProjectSyncState.objects.filter(last_success_at__isnull=False)
            .order_by("-last_success_at")
            .values_list("last_success_at", flat=True)
            .first()
        )
    except Exception:  # noqa: BLE001 - never let this break the health endpoint
        return None
    return value.isoformat() if value else None


def _project_counts() -> dict[str, int | None]:
    """Project counts, or ``None`` if the database is unavailable."""
    try:
        from pullini.projects.models import Project

        return {
            "total": Project.objects.count(),
            "enabled": Project.objects.filter(enabled=True).count(),
        }
    except Exception:  # noqa: BLE001 - never let a count break the health endpoint
        return {"total": None, "enabled": None}
