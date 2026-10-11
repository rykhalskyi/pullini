"""Custom Django admin site: only superusers may open the admin (D-35).

Pullini has two built-in roles: a single admin (the Django superuser) that manages
projects and accounts, and non-staff readers (D-27). A staff-but-not-superuser
flag must therefore not grant access to ``/admin/``.
"""

from __future__ import annotations

from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.http import HttpRequest


class PulliniAdminSite(AdminSite):
    """Restrict the Django admin to active superusers."""

    def has_permission(self, request: HttpRequest) -> bool:
        return request.user.is_active and request.user.is_superuser


class PulliniAdminConfig(AdminConfig):
    """Point Django's default admin site at ``PulliniAdminSite`` (D-35)."""

    default_site = "pullini.core.admin.PulliniAdminSite"
