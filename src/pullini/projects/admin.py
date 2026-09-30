"""Admin configuration for projects.

Project management (add/configure/delete) is exposed through Django's built-in
admin, which is gated to the single admin role. Public wiki pages stay
read-only (HLD §4).
"""

from __future__ import annotations

from django.contrib import admin

from pullini.projects.models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "branch",
        "docs_folder",
        "update_interval_minutes",
        "enabled",
        "updated_at",
    )
    list_filter = ("enabled",)
    list_editable = ("enabled",)
    search_fields = ("name", "repo_url", "docs_folder")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "enabled")}),
        ("Git source", {"fields": ("repo_url", "branch", "docs_folder")}),
        ("Synchronization", {"fields": ("update_interval_minutes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
