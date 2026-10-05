"""Core views: the landing page and the health endpoint."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from pullini.core.health import collect_status
from pullini.favorites.services import recent_favorites
from pullini.projects.models import Project


def _may_view_details(request: HttpRequest) -> bool:
    """Only staff (or local DEBUG) see paths, versions and error strings."""
    return request.user.is_staff or settings.DEBUG


def home(request: HttpRequest):
    return render(
        request,
        "home.html",
        {
            "status": collect_status(detailed=_may_view_details(request)),
            "projects": Project.objects.filter(enabled=True),
            "favorites": recent_favorites(request.user),
        },
    )


def healthz(request: HttpRequest) -> JsonResponse:
    status = collect_status(detailed=_may_view_details(request))
    code = 200 if status["status"] == "healthy" else 503
    return JsonResponse(status, status=code)


def livez(request: HttpRequest) -> JsonResponse:
    """Dependency-free liveness probe: reports only that the process responds."""
    return JsonResponse({"status": "ok"})
