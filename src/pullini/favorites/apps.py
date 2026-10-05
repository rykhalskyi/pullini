"""Application configuration for the favorites app."""

from __future__ import annotations

from django.apps import AppConfig


class FavoritesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pullini.favorites"
    verbose_name = "Favorites"
