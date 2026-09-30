"""Read-only wiki views: tree, index, recent, page and assets (HLD §10)."""

from __future__ import annotations

from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from pullini.projects.views import visible_projects
from pullini.wiki.generation import docs_path
from pullini.wiki.models import Page


def _get_project(request: HttpRequest, slug: str):
    return get_object_or_404(visible_projects(request.user), slug=slug)


def _breadcrumbs(page: Page) -> list[dict[str, str]]:
    parts = page.url_path.split("/")
    return [
        {"name": part, "path": "/".join(parts[: index + 1])} for index, part in enumerate(parts)
    ]


def wiki_tree(request: HttpRequest, slug: str) -> HttpResponse:
    project = _get_project(request, slug)
    pages = list(project.pages.all())
    return render(request, "wiki/tree.html", {"project": project, "pages": pages})


def wiki_recent(request: HttpRequest, slug: str) -> HttpResponse:
    project = _get_project(request, slug)
    pages = project.pages.order_by("-updated_at")[:50]
    return render(request, "wiki/recent.html", {"project": project, "pages": pages})


def wiki_page(request: HttpRequest, slug: str, page_path: str) -> HttpResponse:
    project = _get_project(request, slug)
    page = get_object_or_404(Page, project=project, url_path=page_path)
    return render(
        request,
        "wiki/page.html",
        {"project": project, "page": page, "breadcrumbs": _breadcrumbs(page)},
    )


def wiki_asset(request: HttpRequest, slug: str, asset_path: str) -> HttpResponse:
    project = _get_project(request, slug)
    root = docs_path(project).resolve()
    target = (root / asset_path).resolve()
    if not target.is_file() or not target.is_relative_to(root):
        raise Http404
    return FileResponse(open(target, "rb"))
