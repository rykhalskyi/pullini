"""Application configuration for the Q&A app."""

from __future__ import annotations

from django.apps import AppConfig


class QandaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pullini.qanda"
    verbose_name = "Q&A"
