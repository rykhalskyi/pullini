"""Public, read-only project views (HLD §4, §11)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from pullini.projects.models import Project


def visible_projects(user):
    """Enabled projects are public; staff may also see disabled ones."""
    queryset = Project.objects.all()
    if user.is_authenticated and user.is_staff:
        return queryset
    return queryset.filter(enabled=True)


def project_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "projects/project_list.html",
        {"projects": visible_projects(request.user)},
    )


def project_detail(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_object_or_404(visible_projects(request.user), slug=slug)
    return render(request, "projects/project_detail.html", {"project": project})
