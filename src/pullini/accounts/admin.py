"""Django admin registration for accounts.

Personal access tokens stay view-only (D-34). The built-in ``UserAdmin`` is
replaced so an administrator can create a user without choosing a password:
the admin receives a one-time setup link to share, and the user picks their
own password.
"""

from __future__ import annotations

from contextlib import suppress

from django.conf import settings
from django.contrib import admin
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.admin.utils import unquote
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import path, reverse

from pullini.accounts.forms import InviteUserCreationForm
from pullini.accounts.invites import (
    build_password_setup_url,
    format_setup_timeout,
    pop_setup_link,
    remember_setup_link,
)
from pullini.accounts.models import PersonalAccessToken

with suppress(NotRegistered):
    admin.site.unregister(User)


@admin.register(User)
class PulliniUserAdmin(DjangoUserAdmin):
    add_form = InviteUserCreationForm
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("username",)}),)
    change_form_template = "admin/auth/user/change_form.html"
    add_form_template = "admin/auth/user/change_form.html"
    list_display = (*DjangoUserAdmin.list_display, "password_status")

    @admin.display(description="Password")
    def password_status(self, obj: User) -> str:
        return "Set" if obj.has_usable_password() else "Not set"

    def get_urls(self):
        return [
            path(
                "<path:object_id>/setup-link/",
                self.admin_site.admin_view(self.setup_link_view),
                name="auth_user_setup_link",
            ),
            *super().get_urls(),
        ]

    def save_model(self, request, obj, form, change) -> None:
        if not change:
            obj.set_unusable_password()
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        self._flash_setup_link(request, obj)
        return super().response_add(request, obj, post_url_continue)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        if change and obj is not None:
            setup_url = pop_setup_link(request, obj)
            if setup_url:
                context["password_setup_url"] = setup_url
                context["password_setup_expiry"] = format_setup_timeout(
                    settings.PASSWORD_RESET_TIMEOUT
                )
        return super().render_change_form(
            request, context, add=add, change=change, form_url=form_url, obj=obj
        )

    def setup_link_view(self, request, object_id):
        """Remove the current password and issue a fresh one-time setup link."""
        if request.method != "POST":
            return HttpResponseNotAllowed(["POST"])

        user = self.get_object(request, unquote(object_id))
        if user is None:
            raise Http404
        if not self.has_change_permission(request, user):
            raise PermissionDenied

        user.set_unusable_password()
        user.save(update_fields=["password"])
        self.log_change(request, user, "Password removed and a new setup link generated.")
        self._flash_setup_link(request, user)
        self.message_user(request, "Password removed and a new setup link generated.")
        return redirect(reverse("admin:auth_user_change", args=[user.pk]))

    def _flash_setup_link(self, request, user: User) -> None:
        remember_setup_link(request, user, build_password_setup_url(request, user))


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
