"""Application configuration for the projects app."""

from __future__ import annotations

from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pullini.projects"
    verbose_name = "Projects"

    def ready(self) -> None:
        from pullini.projects import signals  # noqa: F401 - register signal handlers
