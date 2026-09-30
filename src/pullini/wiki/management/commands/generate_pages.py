"""Regenerate wiki pages from the local clones (useful after manual changes)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from pullini.projects.models import Project
from pullini.wiki.generation import generate_pages


class Command(BaseCommand):
    help = "Generate wiki pages from each project's cloned documentation folder."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--project", help="Only generate for this project slug.")

    def handle(self, *args, **options) -> None:
        projects = Project.objects.all()
        if options["project"]:
            projects = projects.filter(slug=options["project"])

        total = 0
        for project in projects:
            changed = generate_pages(project)
            total += changed
            self.stdout.write(f"{project.slug}: {changed} page(s) generated")
        self.stdout.write(f"done, {total} page(s) generated")
