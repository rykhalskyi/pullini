"""Django admin registration for personal access tokens (diagnostics only).

Tokens are created and revoked at ``/settings/tokens/``; the raw secret is never
stored, so the admin only ever shows the public prefix.
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
