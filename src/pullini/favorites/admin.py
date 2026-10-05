"""Django admin registration for favorites (read-mostly diagnostics)."""

from __future__ import annotations

from django.contrib import admin

from pullini.favorites.models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "page", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "page__title", "page__path")
    readonly_fields = ("created_at",)
