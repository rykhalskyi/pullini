"""Per-user favorites of generated wiki pages (E6, D-26).

A favorite references the derived ``Page`` row, which is stable across content
updates because generation uses ``update_or_create`` keyed by ``(project, path)``.
When a page disappears from its repository the row (and its favorites) cascade
away.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    page = models.ForeignKey(
        "wiki.Page",
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "page"],
                name="unique_favorite_per_user_page",
            ),
        ]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user}:{self.page}"
