"""Shared test fixtures: a local bare Git repository and a Project bound to it."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@dataclass
class RemoteRepo:
    bare: Path
    work: Path

    def commit(self, content: str) -> str:
        (self.work / "docs" / "index.md").write_text(content)
        git(self.work, "add", ".")
        git(self.work, "commit", "-m", "update")
        git(self.work, "push", "origin", "main")
        return content

    def write(self, relpath: str, content: str) -> None:
        path = self.work / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        git(self.work, "add", ".")
        git(self.work, "commit", "-m", f"update {relpath}")
        git(self.work, "push", "origin", "main")

    def remove(self, relpath: str) -> None:
        git(self.work, "rm", relpath)
        git(self.work, "commit", "-m", f"remove {relpath}")
        git(self.work, "push", "origin", "main")


@pytest.fixture
def remote_repo(tmp_path, monkeypatch) -> RemoteRepo:
    for var in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(var, "Test")
    for var in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(var, "test@example.com")

    bare = tmp_path / "remote.git"
    work = tmp_path / "work"
    git(tmp_path, "init", "--bare", "-b", "main", str(bare))
    git(tmp_path, "clone", str(bare), str(work))
    (work / "docs").mkdir()
    (work / "docs" / "index.md").write_text("# Home\n")
    (work / "app").mkdir()
    (work / "app" / "main.py").write_text("print('hi')\n")
    git(work, "add", ".")
    git(work, "commit", "-m", "initial")
    git(work, "push", "origin", "main")
    return RemoteRepo(bare=bare, work=work)


@pytest.fixture
def project(settings, tmp_path, remote_repo):
    from pullini.projects.models import Project

    settings.REPOSITORIES_DIR = tmp_path / "repositories"
    return Project.objects.create(
        name="Payments",
        repo_url=f"file://{remote_repo.bare}",
        branch="main",
    )
