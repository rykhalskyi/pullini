"""Search backends (HLD §9).

Search is abstracted behind a small interface so the same code runs on SQLite
(portable ORM matching) and PostgreSQL (native full-text search). The derived
``Page`` table *is* the index: it is regenerated when project content changes,
so results are always current and no separate index service is required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.db import connection
from django.db.models import Q

from pullini.wiki.models import Page

SNIPPET_WIDTH = 200


@dataclass
class SearchResult:
    page: Page
    rank: float
    snippet: str


def _terms(query: str) -> list[str]:
    return [term for term in re.split(r"\s+", query.strip()) if term]


def make_snippet(text: str, terms: list[str], width: int = SNIPPET_WIDTH) -> str:
    """A short contextual window around the first matching term."""
    if not text:
        return ""
    lowered = text.lower()
    position = -1
    for term in terms:
        found = lowered.find(term.lower())
        if found != -1 and (position == -1 or found < position):
            position = found

    if position == -1:
        window = text[:width]
        return window + ("…" if len(text) > width else "")

    start = max(0, position - width // 3)
    window = text[start : start + width]
    prefix = "…" if start > 0 else ""
    suffix = "…" if start + width < len(text) else ""
    return f"{prefix}{window.strip()}{suffix}"


class SimpleSearchBackend:
    """Portable matching using the ORM; correct on any database engine."""

    name = "simple"

    def search(self, query: str, *, project=None, limit: int = 20) -> list[SearchResult]:
        terms = _terms(query)
        if not terms:
            return []

        pages = Page.objects.select_related("project").filter(project__enabled=True)
        if project is not None:
            pages = pages.filter(project=project)

        match = Q()
        for term in terms:
            match &= (
                Q(title__icontains=term)
                | Q(path__icontains=term)
                | Q(plain_text__icontains=term)
                | Q(project__name__icontains=term)
            )

        scored = [
            SearchResult(page, self._score(page, terms), make_snippet(page.plain_text, terms))
            for page in pages.filter(match)[:500]
        ]
        scored.sort(key=lambda result: (-result.rank, result.page.title.lower()))
        return scored[:limit]

    @staticmethod
    def _score(page: Page, terms: list[str]) -> float:
        title = page.title.lower()
        path = page.path.lower()
        body = page.plain_text.lower()
        project_name = page.project.name.lower()
        return float(
            sum(
                5 * title.count(term.lower())
                + 3 * path.count(term.lower())
                + 2 * project_name.count(term.lower())
                + body.count(term.lower())
                for term in terms
            )
        )


class PostgresSearchBackend(SimpleSearchBackend):
    """Native PostgreSQL full-text search (no extra infrastructure)."""

    name = "postgres"

    def search(self, query: str, *, project=None, limit: int = 20) -> list[SearchResult]:
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        terms = _terms(query)
        if not terms:
            return []

        pages = Page.objects.select_related("project").filter(project__enabled=True)
        if project is not None:
            pages = pages.filter(project=project)

        vector = (
            SearchVector("title", weight="A")
            + SearchVector("path", weight="B")
            + SearchVector("plain_text", weight="C")
        )
        search_query = SearchQuery(query, search_type="websearch")
        pages = (
            pages.annotate(rank=SearchRank(vector, search_query))
            .filter(
                Q(rank__gte=0.01)
                | Q(title__icontains=query)
                | Q(path__icontains=query)
                | Q(project__name__icontains=query)
            )
            .order_by("-rank", "title")
        )

        return [
            SearchResult(page, float(page.rank or 0), make_snippet(page.plain_text, terms))
            for page in pages[:limit]
        ]


def get_backend() -> SimpleSearchBackend:
    if connection.vendor == "postgresql":
        return PostgresSearchBackend()
    return SimpleSearchBackend()
