"""Thin wrapper around the Git CLI (HLD §6).

Pullini only needs a working tree, never history, so clones are shallow and
single-branch. Using the CLI keeps the dependency surface small and matches the
"Git CLI / Git library" choice in the HLD.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

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


def clone(repo_url: str, branch: str, dest: Path, *, sparse_path: str | None = None) -> None:
    """Clone a shallow, single-branch working tree.

    When ``sparse_path`` is given the clone first tries a partial clone
    (``--filter=blob:none``) limited to that path via sparse checkout, so huge
    repositories only download the blobs under the documentation folder. Servers
    that do not support partial clone either ignore the filter (git warns and
    downloads everything anyway) or refuse the clone; in the latter case we
    retry with a plain shallow clone of the whole branch.
    """
    if sparse_path:
        try:
            _clone_sparse(repo_url, branch, dest, sparse_path)
            return
        except GitError as exc:
            logger.warning(
                "sparse clone of %s failed, falling back to a full clone: %s",
                repo_url,
                exc,
            )
            if dest.exists():
                shutil.rmtree(dest)

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


def _clone_sparse(repo_url: str, branch: str, dest: Path, sparse_path: str) -> None:
    run_git(
        "clone",
        "--depth",
        "1",
        "--single-branch",
        "--branch",
        branch,
        "--filter=blob:none",
        "--sparse",
        repo_url,
        str(dest),
    )
    sparse_checkout_set(dest, sparse_path)


def sparse_checkout_set(repo: Path, path: str) -> None:
    """Limit the working tree to ``path`` (cone mode)."""
    run_git("sparse-checkout", "set", "--cone", path, cwd=repo)


def is_sparse(repo: Path) -> bool:
    try:
        return run_git("config", "--bool", "--get", "core.sparseCheckout", cwd=repo) == "true"
    except GitError:
        return False


def fetch_and_reset(branch: str, dest: Path) -> None:
    run_git("fetch", "--depth", "1", "origin", branch, cwd=dest)
    run_git("reset", "--hard", "FETCH_HEAD", cwd=dest)
