"""Management command used by the scheduler to synchronize projects (HLD §7)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from pullini.projects.models import Project, SyncStatus
from pullini.projects.sync import sync_project


class Command(BaseCommand):
    help = "Clone or update each enabled project's Git repository."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--project",
            help="Sync only the project with this slug (forces the sync).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Sync now, ignoring each project's update interval.",
        )

    def handle(self, *args, **options) -> None:
        if options["project"]:
            projects = list(Project.objects.filter(slug=options["project"]))
            force = True
            if not projects:
                self.stderr.write(f"no project with slug {options['project']!r}")
                return
        else:
            projects = list(Project.objects.filter(enabled=True))
            force = options["force"]

        if not projects:
            self.stdout.write("no projects to sync")
            return

        errors = 0
        for project in projects:
            state = sync_project(project, force=force)
            if state.status == SyncStatus.ERROR:
                errors += 1
                self.stderr.write(f"{project.slug}: error - {state.last_error}")
            else:
                commit = state.last_commit[:8] or "-"
                self.stdout.write(f"{project.slug}: {state.status} @ {commit}")

        self.stdout.write(f"synced {len(projects)} project(s), {errors} error(s)")
