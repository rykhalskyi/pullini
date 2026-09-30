"""Public, read-only project views and the staff-only refresh action (HLD §4, §11)."""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from pullini.projects.models import Project, ProjectSyncState, SyncStatus
from pullini.projects.sync import sync_project


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
    sync_state = ProjectSyncState.objects.filter(project=project).first()
    return render(
        request,
        "projects/project_detail.html",
        {
            "project": project,
            "sync_state": sync_state,
            "page_count": project.pages.count(),
        },
    )


@require_POST
@login_required
def project_refresh(request: HttpRequest, slug: str) -> HttpResponse:
    """Trigger an immediate synchronization (admin only, HLD §4)."""
    if not request.user.is_staff:
        raise PermissionDenied

    project = get_object_or_404(Project, slug=slug)
    state = sync_project(project, force=True)

    if state.status == SyncStatus.ERROR:
        messages.error(request, f"{project.name}: {state.last_error}")
    else:
        messages.success(request, f"{project.name} synchronized from Git.")

    next_url = request.POST.get("next")
    if not next_url or not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("projects:detail", kwargs={"slug": project.slug})
    return redirect(next_url)
