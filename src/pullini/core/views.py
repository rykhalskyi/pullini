"""Core views: the landing page and the health endpoint."""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.shortcuts import render

from pullini.core.health import collect_status
from pullini.projects.models import Project


def home(request: HttpRequest):
    return render(
        request,
        "home.html",
        {
            "status": collect_status(),
            "projects": Project.objects.filter(enabled=True),
        },
    )


def healthz(request: HttpRequest) -> JsonResponse:
    status = collect_status()
    code = 200 if status["status"] == "healthy" else 503
    return JsonResponse(status, status=code)
