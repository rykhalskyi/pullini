"""Admin configuration for projects.

Project management (add/configure/delete/refresh) is exposed through Django's
built-in admin, which is gated to the single admin role. Public wiki pages stay
read-only (HLD §4).
"""

from __future__ import annotations

from django.contrib import admin, messages

from pullini.projects.models import Project, SyncStatus
from pullini.projects.sync import sync_project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "branch",
        "docs_folder",
        "update_interval_minutes",
        "enabled",
        "sync_status",
        "updated_at",
    )
    list_filter = ("enabled",)
    list_editable = ("enabled",)
    search_fields = ("name", "repo_url", "docs_folder")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    actions = ("refresh_now",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "enabled")}),
        ("Git source", {"fields": ("repo_url", "branch", "docs_folder")}),
        ("Synchronization", {"fields": ("update_interval_minutes",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="Sync")
    def sync_status(self, obj: Project) -> str:
        state = getattr(obj, "sync_state", None)
        return state.get_status_display() if state else "-"

    @admin.action(description="Refresh now (synchronize from Git)")
    def refresh_now(self, request, queryset) -> None:
        synced = failed = 0
        for project in queryset:
            state = sync_project(project, force=True)
            if state.status == SyncStatus.ERROR:
                failed += 1
                self.message_user(
                    request,
                    f"{project.name}: {state.last_error}",
                    level=messages.ERROR,
                )
            else:
                synced += 1
        if synced:
            self.message_user(request, f"Synchronized {synced} project(s).")
