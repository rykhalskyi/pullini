"""Project lifecycle hooks (T15).

Deleting a project must also discard its on-disk clone and lock file. The
cleanup runs on commit so a rolled-back transaction never leaves the database
row without its working tree.
"""

from __future__ import annotations

import contextlib
import shutil

from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from pullini.projects.models import Project
from pullini.projects.sync import _lock_path, repository_path


@receiver(post_delete, sender=Project)
def remove_project_clone(sender, instance: Project, **kwargs) -> None:
    clone = repository_path(instance)
    lock = _lock_path(instance)

    def cleanup() -> None:
        shutil.rmtree(clone, ignore_errors=True)
        lock.unlink(missing_ok=True)
        # Drop the per-user directory once its last project is gone.
        with contextlib.suppress(OSError):
            clone.parent.rmdir()

    transaction.on_commit(cleanup)
