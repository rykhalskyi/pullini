"""Application configuration for the core app."""

from __future__ import annotations

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pullini.core"

    def ready(self) -> None:
        from pullini.core.health import ensure_data_dirs

        ensure_data_dirs()
