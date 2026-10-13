"""Application configuration for the quizzes app."""

from __future__ import annotations

from django.apps import AppConfig


class QuizzesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pullini.quizzes"
    verbose_name = "Quizzes"
