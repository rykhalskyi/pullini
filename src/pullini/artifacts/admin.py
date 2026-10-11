"""Django admin registration for artifacts.

The web is read-only (D-24); artifacts are created and mutated through the
artifact REST API (T5), so this is a diagnostics surface.
"""

from __future__ import annotations

from django.contrib import admin

from pullini.artifacts.models import Artifact


@admin.register(Artifact)
class ArtifactAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "slug", "visibility", "updated_at")
    list_filter = ("visibility", "updated_at")
    search_fields = ("user__username", "title", "slug")
    readonly_fields = ("html", "plain_text", "content_hash", "created_at", "updated_at")
