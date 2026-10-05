"""Project visibility policy shared by views and services (HLD §4)."""

from __future__ import annotations

from pullini.projects.models import Project


def visible_projects(user):
    """Enabled projects are public; staff may also see disabled ones."""
    queryset = Project.objects.all()
    if user.is_authenticated and user.is_staff:
        return queryset
    return queryset.filter(enabled=True)
