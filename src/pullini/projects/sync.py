"""Project synchronization (HLD §6, §7).

Each enabled project keeps a persistent shallow clone under
``DATA_DIR/repositories/<slug>``. Synchronization is triggered on each
project's interval (or manually) and must never take the application down: a
failed sync records an error and leaves the last good clone in place.
"""

from __future__ import annotations

import fcntl
import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from pullini.projects import git
from pullini.projects.models import Project, ProjectSyncState, SyncStatus


class SyncInProgress(Exception):
    """Another process already holds this project's synchronization lock."""


def repository_path(project: Project) -> Path:
    return Path(settings.REPOSITORIES_DIR) / project.slug


def _lock_path(project: Project) -> Path:
    return Path(settings.REPOSITORIES_DIR) / f"{project.slug}.lock"


@contextmanager
def repository_lock(project: Project) -> Iterator[None]:
    """Non-blocking exclusive lock so a manual and scheduled sync cannot collide."""
    lock_path = _lock_path(project)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise SyncInProgress(project.slug) from exc
        yield
    finally:
        os.close(descriptor)


def get_sync_state(project: Project) -> ProjectSyncState:
    state, _ = ProjectSyncState.objects.get_or_create(project=project)
    return state


def is_due(project: Project, state: ProjectSyncState, *, now=None) -> bool:
    if state.last_attempt_at is None:
        return True
    now = now or timezone.now()
    interval = timedelta(minutes=project.update_interval_minutes)
    return now - state.last_attempt_at >= interval


def sync_repository(project: Project) -> str:
    """Clone or update the project's working tree; return the checked-out commit."""
    dest = repository_path(project)
    if git.is_git_repository(dest) and git.current_branch(dest) == project.branch:
        git.fetch_and_reset(project.branch, dest)
    else:
        if dest.exists():
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        git.clone(project.repo_url, project.branch, dest)
    return git.current_commit(dest)


def sync_project(project: Project, *, force: bool = False) -> ProjectSyncState:
    """Synchronize one project, recording the outcome. Never raises on failure."""
    state = get_sync_state(project)
    if not force and not is_due(project, state):
        return state

    try:
        with repository_lock(project):
            state.status = SyncStatus.RUNNING
            state.last_attempt_at = timezone.now()
            state.save()

            commit = sync_repository(project)

            state.last_commit = commit
            state.last_success_at = timezone.now()
            state.status = SyncStatus.OK
            state.last_error = ""
            state.save()
    except SyncInProgress:
        # Leave the previous state untouched; another run will report it.
        pass
    except Exception as exc:  # noqa: BLE001 - a failed sync must not crash the caller
        state.status = SyncStatus.ERROR
        state.last_error = str(exc)
        state.last_attempt_at = timezone.now()
        state.save()
    return state


def sync_due_projects(*, force: bool = False) -> list[ProjectSyncState]:
    """Sync every enabled project that is due (or all of them when forced)."""
    return [sync_project(project, force=force) for project in Project.objects.filter(enabled=True)]
