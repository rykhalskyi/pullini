"""Project views (T15, HLD §4, §11).

Public surfaces are owner-private: a user only ever sees their own projects
(superusers see all). Non-admin owners manage their projects through the
in-app page rather than the Django admin.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from pullini.projects.access import can_manage, visible_projects
from pullini.projects.forms import ProjectForm
from pullini.projects.models import ProjectSyncState, SyncStatus
from pullini.projects.sync import sync_project
from pullini.qanda.services import qanda_for_project
from pullini.quizzes.services import quizzes_for_project


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
            "quizzes": quizzes_for_project(request.user, project),
            "qanda": qanda_for_project(request.user, project),
            "can_manage": can_manage(request.user, project),
        },
    )


@login_required
def project_manage(request: HttpRequest) -> HttpResponse:
    """Owner management page: list projects and offer the add form (T15)."""
    return render(
        request,
        "projects/manage.html",
        {
            "projects": visible_projects(request.user),
            "form": ProjectForm(),
        },
    )


@login_required
@require_POST
def project_create(request: HttpRequest) -> HttpResponse:
    """Create a project owned by the caller, then immediately sync it (T15)."""
    form = ProjectForm(request.POST)
    project = None
    if form.is_valid():
        project = form.save(commit=False)
        project.user = request.user
        try:
            # Re-validate on the owned instance so the per-owner uniqueness
            # constraints are checked with the owner set.
            project.full_clean(exclude=["slug"])
        except ValidationError as exc:
            form.add_error(None, exc)

    if project is None or form.errors:
        return render(
            request,
            "projects/manage.html",
            {"projects": visible_projects(request.user), "form": form},
            status=400,
        )

    project.save()

    state = sync_project(project, force=True)
    if state.status == SyncStatus.ERROR:
        messages.warning(
            request,
            f"Project created, but the first sync failed: {state.last_error}",
        )
    else:
        messages.success(request, f"{project.name} created and synchronized from Git.")
    return redirect("projects:manage")


@login_required
@require_POST
def project_delete(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_object_or_404(visible_projects(request.user), slug=slug)
    if not can_manage(request.user, project):
        raise PermissionDenied
    name = project.name
    project.delete()
    messages.success(request, f"{name} deleted.")
    return redirect("projects:manage")


@require_POST
@login_required
def project_refresh(request: HttpRequest, slug: str) -> HttpResponse:
    """Trigger an immediate synchronization (owner or superuser, HLD §4)."""
    project = get_object_or_404(visible_projects(request.user), slug=slug)
    if not can_manage(request.user, project):
        raise PermissionDenied
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
