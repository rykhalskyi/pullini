"""Thin wrapper around the Git CLI (HLD §6).

Pullini only needs a working tree, never history, so clones are shallow and
single-branch. Using the CLI keeps the dependency surface small and matches the
"Git CLI / Git library" choice in the HLD.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 300


class GitError(RuntimeError):
    """A git command failed or could not be started."""


def git_env() -> dict[str, str]:
    """Environment that keeps git non-interactive.

    Without this a private/unknown remote blocks a worker waiting for
    credentials or a host-key prompt until the timeout expires.
    """
    env = os.environ.copy()
    env.setdefault("GIT_TERMINAL_PROMPT", "0")
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    return env


def run_git(*args: str, cwd: Path | None = None, timeout: int = GIT_TIMEOUT_SECONDS) -> str:
    command = ["git", *args]
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=git_env(),
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitError(f"could not run git {args[0]}: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GitError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def is_git_repository(path: Path) -> bool:
    return (path / ".git").exists()


def current_branch(repo: Path) -> str:
    return run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=repo)


def current_commit(repo: Path) -> str:
    return run_git("rev-parse", "HEAD", cwd=repo)


def clone(repo_url: str, branch: str, dest: Path) -> None:
    run_git(
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--branch",
        branch,
        repo_url,
        str(dest),
    )


def fetch_and_reset(branch: str, dest: Path) -> None:
    run_git("fetch", "--depth", "1", "origin", branch, cwd=dest)
    run_git("reset", "--hard", "FETCH_HEAD", cwd=dest)
