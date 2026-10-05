"""Query helpers shared by the favorites views and the pages that embed a star."""

from __future__ import annotations

from django.db.models import QuerySet

from pullini.favorites.models import Favorite

HOME_FAVORITES_LIMIT = 6


def recent_favorites(user, limit: int = HOME_FAVORITES_LIMIT) -> QuerySet[Favorite]:
    """The user's most recently starred pages, newest first."""
    if not user.is_authenticated:
        return Favorite.objects.none()
    return (
        Favorite.objects.filter(user=user)
        .select_related("page", "page__project")
        .order_by("-created_at")[:limit]
    )


def is_favorite(user, page) -> bool:
    if not user.is_authenticated:
        return False
    return Favorite.objects.filter(user=user, page=page).exists()
