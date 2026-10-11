"""Django admin registration for personal access tokens (view-only diagnostics).

Tokens are created and revoked exclusively at ``/settings/tokens/``; the raw
secret is never stored, so the admin only ever shows the public prefix. Creation
is disabled because the secret generator lives in the user flow -- an admin-made
row would carry an empty prefix/hash and could never authenticate.
"""

from __future__ import annotations

from django.contrib import admin

from pullini.accounts.models import PersonalAccessToken


@admin.register(PersonalAccessToken)
class PersonalAccessTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "prefix", "created_at", "last_used_at", "revoked_at")
    list_filter = ("created_at", "revoked_at")
    search_fields = ("user__username", "name", "prefix")
    readonly_fields = ("prefix", "token_hash", "created_at", "last_used_at")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
