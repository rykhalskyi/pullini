"""Search service entry point (HLD §9)."""

from __future__ import annotations

from pullini.search.backends import SearchResult, get_backend


def search(query: str, *, user, project=None, limit: int = 20) -> list[SearchResult]:
    """Search pages and the caller's own artifacts.

    Artifacts are private and only ever returned to their owner, so they are
    searched only for authenticated users and never in a project-scoped search
    (artifacts do not belong to a project). Results are grouped artifacts first,
    then pages, each ordered by relevance.
    """
    query = (query or "").strip()
    if not query:
        return []

    backend = get_backend()
    artifacts = backend.search_artifacts(query, user=user, limit=limit) if project is None else []
    pages = backend.search_pages(query, user=user, project=project, limit=limit)
    return [*artifacts, *pages]


def search_pages(query: str, *, user, project=None, limit: int = 20) -> list[SearchResult]:
    query = (query or "").strip()
    if not query:
        return []
    return get_backend().search_pages(query, user=user, project=project, limit=limit)
