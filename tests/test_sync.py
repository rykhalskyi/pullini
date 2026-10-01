"""Synchronization tests using a local bare Git repository (no network)."""

from __future__ import annotations

import shutil
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from pullini.core.health import collect_status
from pullini.projects import git
from pullini.projects.git import git_env
from pullini.projects.models import SyncStatus
from pullini.projects.sync import (
    SyncInProgress,
    is_due,
    repository_lock,
    repository_path,
    sync_project,
)

pytestmark = pytest.mark.django_db


def test_sync_clones_repository(project):
    state = sync_project(project, force=True)

    repo = repository_path(project)
    assert state.status == SyncStatus.OK
    assert state.last_error == ""
    assert state.last_commit
    assert state.last_success_at is not None
    assert (repo / ".git").is_dir()
    assert (repo / "docs" / "index.md").read_text() == "# Home\n"


def test_sync_uses_sparse_checkout(project):
    sync_project(project, force=True)

    repo = repository_path(project)
    assert (repo / "docs" / "index.md").exists()
    # Only the configured docs folder is checked out, not the rest of the repo.
    assert not (repo / "app").exists()
    assert git.is_sparse(repo)


def test_sync_falls_back_to_full_clone_when_filter_unsupported(project, monkeypatch):
    real_run_git = git.run_git

    def flaky(*args, **kwargs):
        if args and args[0] == "clone" and "--filter=blob:none" in args:
            raise git.GitError("server does not support filter")
        return real_run_git(*args, **kwargs)

    monkeypatch.setattr(git, "run_git", flaky)

    state = sync_project(project, force=True)

    repo = repository_path(project)
    assert state.status == SyncStatus.OK
    assert (repo / "docs" / "index.md").exists()
    # The whole branch is present after the fallback clone.
    assert (repo / "app" / "main.py").exists()
    assert not git.is_sparse(repo)


def test_sparse_checkout_follows_docs_folder(project, remote_repo):
    sync_project(project, force=True)

    remote_repo.write("guides/start.md", "# Start\n")
    project.docs_folder = "guides"
    project.save()

    sync_project(project, force=True)

    repo = repository_path(project)
    assert (repo / "guides" / "start.md").exists()
    assert not (repo / "docs").exists()
    assert not (repo / "app").exists()


def test_sync_detects_new_commit(project, remote_repo):
    first = sync_project(project, force=True)

    remote_repo.commit("# Home\n\nMore.\n")
    second = sync_project(project, force=True)

    assert second.last_commit != first.last_commit
    assert (repository_path(project) / "docs" / "index.md").read_text() == "# Home\n\nMore.\n"


def test_sync_failure_records_error_and_keeps_last_clone(project, remote_repo):
    sync_project(project, force=True)
    shutil.rmtree(remote_repo.bare)

    state = sync_project(project, force=True)

    assert state.status == SyncStatus.ERROR
    assert state.last_error
    # The last good working tree is left in place (HLD §15).
    assert (repository_path(project) / "docs" / "index.md").exists()


def test_not_due_is_skipped(project, remote_repo):
    sync_project(project, force=True)
    shutil.rmtree(remote_repo.bare)

    state = sync_project(project, force=False)

    assert state.status == SyncStatus.OK


def test_force_bypasses_interval(project, remote_repo):
    sync_project(project, force=True)
    shutil.rmtree(remote_repo.bare)

    state = sync_project(project, force=True)

    assert state.status == SyncStatus.ERROR


def test_due_after_interval(project):
    state = sync_project(project, force=True)

    state.last_attempt_at = timezone.now() - timedelta(minutes=11)
    state.save()

    assert is_due(project, state) is True


def test_repository_lock_is_exclusive(project):
    with repository_lock(project), pytest.raises(SyncInProgress):  # noqa: SIM117
        with repository_lock(project):
            pass


def test_sync_projects_command(project):
    out = StringIO()

    call_command("sync_projects", "--force", stdout=out)

    assert project.sync_state.status == SyncStatus.OK
    assert "1 project(s)" in out.getvalue()


def test_git_env_is_non_interactive(monkeypatch):
    monkeypatch.delenv("GIT_TERMINAL_PROMPT", raising=False)
    monkeypatch.delenv("GIT_SSH_COMMAND", raising=False)

    env = git_env()

    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert "BatchMode=yes" in env["GIT_SSH_COMMAND"]


def test_health_reports_last_sync(project):
    sync_project(project, force=True)

    assert collect_status()["last_sync"] is not None
