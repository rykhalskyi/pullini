"""Search backends (HLD §9).

Search is abstracted behind a small interface so the same code runs on SQLite
(portable ORM matching) and PostgreSQL (native full-text search). The derived
``Page`` table *is* the index: it is regenerated when project content changes,
so results are always current and no separate index service is required.

Artifacts are searched from the authoritative ``Artifact`` table, whose derived
``plain_text``/``html`` fields are already kept current. Artifacts are private
to their owner, so artifact search is always scoped to ``user``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.db import connection
from django.db.models import Q

from pullini.artifacts.models import Artifact
from pullini.projects.access import visible_projects
from pullini.wiki.models import Page

SNIPPET_WIDTH = 200


@dataclass
class SearchResult:
    kind: str  # "page" | "artifact"
    rank: float
    snippet: str
    page: Page | None = None
    artifact: Artifact | None = None


def _terms(query: str) -> list[str]:
    return [term for term in re.split(r"\s+", query.strip()) if term]


def _is_authenticated(user) -> bool:
    return user is not None and user.is_authenticated


def _any_term(terms: list[str], *fields: str) -> Q:
    """Match rows where every term appears in at least one of ``fields``.

    Keeps the portable ORM fallback (and the PostgreSQL fallback) term-based and
    therefore identical across engines, instead of matching the raw query string.
    """
    match = Q()
    for term in terms:
        condition = Q()
        for field in fields:
            condition |= Q(**{f"{field}__icontains": term})
        match &= condition
    return match


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


def make_artifact_snippet(artifact: Artifact, terms: list[str], width: int = SNIPPET_WIDTH) -> str:
    """Snippet for an artifact, falling back to matched tags when the body has none.

    A tag-only hit would otherwise show an unrelated body excerpt, hiding why the
    artifact matched.
    """
    body = artifact.plain_text or ""
    lowered = body.lower()
    if any(term.lower() in lowered for term in terms):
        return make_snippet(body, terms, width)

    matched = [
        tag.name
        for tag in artifact.tags.all()
        if any(term.lower() in tag.name.lower() for term in terms)
    ]
    if matched:
        return "Tagged: " + ", ".join(matched)
    return make_snippet(body, terms, width)


class SimpleSearchBackend:
    """Portable matching using the ORM; correct on any database engine."""

    name = "simple"

    def search_pages(
        self, query: str, *, user, project=None, limit: int = 20
    ) -> list[SearchResult]:
        terms = _terms(query)
        if not terms:
            return []

        pages = Page.objects.select_related("project").filter(project__in=visible_projects(user))
        if project is not None:
            pages = pages.filter(project=project)

        match = _any_term(terms, "title", "path", "plain_text", "project__name")

        scored = [
            SearchResult(
                "page",
                self._score_page(page, terms),
                make_snippet(page.plain_text, terms),
                page=page,
            )
            for page in pages.filter(match)[:500]
        ]
        scored.sort(key=lambda result: (-result.rank, result.page.title.lower()))
        return scored[:limit]

    def search_artifacts(self, query: str, *, user, limit: int = 20) -> list[SearchResult]:
        terms = _terms(query)
        if not terms or not _is_authenticated(user):
            return []

        artifacts = Artifact.objects.filter(user=user).prefetch_related("tags")

        match = _any_term(terms, "title", "plain_text", "tags__name")

        scored = [
            SearchResult(
                "artifact",
                self._score_artifact(artifact, terms),
                make_artifact_snippet(artifact, terms),
                artifact=artifact,
            )
            for artifact in artifacts.filter(match).distinct()[:500]
        ]
        scored.sort(key=lambda result: (-result.rank, result.artifact.title.lower()))
        return scored[:limit]

    @staticmethod
    def _score_page(page: Page, terms: list[str]) -> float:
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

    @staticmethod
    def _score_artifact(artifact: Artifact, terms: list[str]) -> float:
        title = artifact.title.lower()
        body = artifact.plain_text.lower()
        tags = " ".join(tag.name.lower() for tag in artifact.tags.all())
        return float(
            sum(
                5 * title.count(term.lower())
                + 3 * tags.count(term.lower())
                + body.count(term.lower())
                for term in terms
            )
        )


class PostgresSearchBackend(SimpleSearchBackend):
    """Native PostgreSQL full-text search (no extra infrastructure)."""

    name = "postgres"

    def search_pages(
        self, query: str, *, user, project=None, limit: int = 20
    ) -> list[SearchResult]:
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        terms = _terms(query)
        if not terms:
            return []

        pages = Page.objects.select_related("project").filter(project__in=visible_projects(user))
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
            .filter(Q(rank__gte=0.01) | _any_term(terms, "title", "path", "project__name"))
            .order_by("-rank", "title")
        )

        return [
            SearchResult(
                "page",
                float(page.rank or 0),
                make_snippet(page.plain_text, terms),
                page=page,
            )
            for page in pages[:limit]
        ]

    def search_artifacts(self, query: str, *, user, limit: int = 20) -> list[SearchResult]:
        from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

        terms = _terms(query)
        if not terms or not _is_authenticated(user):
            return []

        vector = SearchVector("title", weight="A") + SearchVector("plain_text", weight="C")
        search_query = SearchQuery(query, search_type="websearch")
        artifacts = (
            Artifact.objects.filter(user=user)
            .prefetch_related("tags")
            .annotate(rank=SearchRank(vector, search_query))
            .filter(Q(rank__gte=0.01) | _any_term(terms, "title", "plain_text", "tags__name"))
            .distinct()
            .order_by("-rank", "title")
        )

        return [
            SearchResult(
                "artifact",
                float(artifact.rank or 0),
                make_artifact_snippet(artifact, terms),
                artifact=artifact,
            )
            for artifact in artifacts[:limit]
        ]


def get_backend() -> SimpleSearchBackend:
    if connection.vendor == "postgresql":
        return PostgresSearchBackend()
    return SimpleSearchBackend()
