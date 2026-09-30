"""Search service entry point (HLD §9)."""

from __future__ import annotations

from pullini.search.backends import SearchResult, get_backend


def search_pages(query: str, *, project=None, limit: int = 20) -> list[SearchResult]:
    query = (query or "").strip()
    if not query:
        return []
    return get_backend().search(query, project=project, limit=limit)
