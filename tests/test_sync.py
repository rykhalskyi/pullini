"""Synchronization tests using a local bare Git repository (no network)."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import timedelta
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.utils import timezone

from pullini.core.health import collect_status
from pullini.projects.models import Project, SyncStatus
from pullini.projects.sync import (
    SyncInProgress,
    is_due,
    repository_lock,
    repository_path,
    sync_project,
)

pytestmark = pytest.mark.django_db


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


@dataclass
class RemoteRepo:
    bare: Path
    work: Path

    def commit(self, content: str) -> str:
        (self.work / "docs" / "index.md").write_text(content)
        _git(self.work, "add", ".")
        _git(self.work, "commit", "-m", "update")
        _git(self.work, "push", "origin", "main")
        return content


@pytest.fixture
def remote_repo(tmp_path, monkeypatch) -> RemoteRepo:
    for var in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(var, "Test")
    for var in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(var, "test@example.com")

    bare = tmp_path / "remote.git"
    work = tmp_path / "work"
    _git(tmp_path, "init", "--bare", "-b", "main", str(bare))
    _git(tmp_path, "clone", str(bare), str(work))
    (work / "docs").mkdir()
    (work / "docs" / "index.md").write_text("# Home\n")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "initial")
    _git(work, "push", "origin", "main")
    return RemoteRepo(bare=bare, work=work)


@pytest.fixture
def project(settings, tmp_path, remote_repo) -> Project:
    settings.REPOSITORIES_DIR = tmp_path / "repositories"
    return Project.objects.create(
        name="Payments",
        repo_url=f"file://{remote_repo.bare}",
        branch="main",
    )


def test_sync_clones_repository(project):
    state = sync_project(project, force=True)

    repo = repository_path(project)
    assert state.status == SyncStatus.OK
    assert state.last_error == ""
    assert state.last_commit
    assert state.last_success_at is not None
    assert (repo / ".git").is_dir()
    assert (repo / "docs" / "index.md").read_text() == "# Home\n"


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


def test_health_reports_last_sync(project):
    sync_project(project, force=True)

    assert collect_status()["last_sync"] is not None
