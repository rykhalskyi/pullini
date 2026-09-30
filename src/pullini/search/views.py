"""Search views: global and project-scoped (HLD §9)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from pullini.projects.views import visible_projects
from pullini.search.services import search_pages


def _render_results(request: HttpRequest, project=None) -> HttpResponse:
    query = (request.GET.get("q") or "").strip()
    results = search_pages(query, project=project)
    return render(
        request,
        "search/results.html",
        {"query": query, "results": results, "project": project},
    )


def global_search(request: HttpRequest) -> HttpResponse:
    return _render_results(request)


def project_search(request: HttpRequest, slug: str) -> HttpResponse:
    project = get_object_or_404(visible_projects(request.user), slug=slug)
    return _render_results(request, project=project)
