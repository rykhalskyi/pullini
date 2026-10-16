"""Project views (T15, HLD §4, §11).

Browsing is owner-private: a user only ever sees their own projects (superusers
can view all for oversight). Owners manage their projects through the in-app
page; superusers manage projects exclusively through the Django admin.
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

from pullini.projects.access import is_owner, visible_projects
from pullini.projects.forms import ProjectForm
from pullini.projects.models import ProjectSyncState, SyncStatus
from pullini.projects.sync import sync_project
from pullini.qanda.services import qanda_for_project
from pullini.quizzes.services import quizzes_for_project

ADMIN_CHANGELIST = "admin:projects_project_changelist"


def _admin_redirect() -> HttpResponse:
    """Superusers manage projects in the Django admin, not in-app (T15)."""
    return redirect(reverse(ADMIN_CHANGELIST))


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
            "is_owner": is_owner(request.user, project),
        },
    )


@login_required
def project_manage(request: HttpRequest) -> HttpResponse:
    """Owner management page: list projects and offer the add form (T15)."""
    if request.user.is_superuser:
        return _admin_redirect()
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
    if request.user.is_superuser:
        return _admin_redirect()

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
    if request.user.is_superuser:
        return _admin_redirect()
    project = get_object_or_404(visible_projects(request.user), slug=slug)
    if not is_owner(request.user, project):
        raise PermissionDenied
    name = project.name
    project.delete()
    messages.success(request, f"{name} deleted.")
    return redirect("projects:manage")


@require_POST
@login_required
def project_refresh(request: HttpRequest, slug: str) -> HttpResponse:
    """Trigger an immediate synchronization (owner only, HLD §4)."""
    if request.user.is_superuser:
        return _admin_redirect()
    project = get_object_or_404(visible_projects(request.user), slug=slug)
    if not is_owner(request.user, project):
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
