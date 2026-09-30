"""Application configuration for the wiki app."""

from __future__ import annotations

from django.apps import AppConfig


class WikiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pullini.wiki"
    verbose_name = "Wiki"
