"""Application configuration for the artifacts app."""

from __future__ import annotations

from django.apps import AppConfig


class ArtifactsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pullini.artifacts"
    verbose_name = "Artifacts"
