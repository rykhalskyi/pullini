"""User-owned Q&A sets about a wiki page or an artifact (E6, T12/D-43…D-45).

A Q&A set is private to its owner and targets **exactly one** source: a
Git-derived :class:`~pullini.wiki.models.Page` or a user-owned
:class:`~pullini.artifacts.models.Artifact`. There is one set per (user, target);
regenerating replaces it (upsert, D-43). Unlike a quiz, a Q&A set is a **static
FAQ**: every answer is visible, nothing is scored and there is no runtime model
(D-44). The source's ``content_hash`` is captured at generation so the UI can
flag a set that has gone stale after a re-sync (D-45).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse

from pullini.wiki import markup


class TargetType(models.TextChoices):
    PAGE = "page", "Page"
    ARTIFACT = "artifact", "Artifact"


class QandA(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="qanda_sets",
    )
    # Exactly one of these is set; both cascade from their source (D-43).
    page = models.ForeignKey(
        "wiki.Page",
        on_delete=models.CASCADE,
        related_name="qanda_sets",
        null=True,
        blank=True,
    )
    artifact = models.ForeignKey(
        "artifacts.Artifact",
        on_delete=models.CASCADE,
        related_name="qanda_sets",
        null=True,
        blank=True,
    )
    target_type = models.CharField(max_length=20, choices=TargetType.choices)

    # The source page's content hash at generation (D-45).
    source_hash = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "page"],
                name="unique_qanda_per_user_page",
            ),
            models.UniqueConstraint(
                fields=["user", "artifact"],
                name="unique_qanda_per_user_artifact",
            ),
            models.CheckConstraint(
                condition=(
                    Q(page__isnull=False, artifact__isnull=True)
                    | Q(page__isnull=True, artifact__isnull=False)
                ),
                name="qanda_exactly_one_target",
            ),
        ]
        indexes = [models.Index(fields=["user", "-updated_at"])]

    def __str__(self) -> str:
        return f"{self.user}:{self.target_type}"

    def get_absolute_url(self) -> str:
        return reverse("qanda:detail", kwargs={"pk": self.pk})

    @property
    def target(self):
        """The single source this Q&A set is about."""
        return self.page if self.page_id else self.artifact

    @property
    def title(self) -> str:
        return self.target.title

    @property
    def source_url(self) -> str:
        if self.page_id:
            return reverse(
                "wiki:page",
                kwargs={"slug": self.page.project.slug, "page_path": self.page.url_path},
            )
        return reverse("artifacts:detail", kwargs={"slug": self.artifact.slug})

    @property
    def item_count(self) -> int:
        return self.items.count()

    @property
    def is_stale(self) -> bool:
        """True when the source changed since the set was generated (D-45)."""
        target = self.target
        return target is not None and self.source_hash != target.content_hash

    @property
    def has_mermaid(self) -> bool:
        return any(markup.has_mermaid(item.answer_html) for item in self.items.all())


class QandAItem(models.Model):
    qanda = models.ForeignKey(
        QandA,
        on_delete=models.CASCADE,
        related_name="items",
    )
    position = models.PositiveIntegerField()
    question = models.TextField()
    # Source Markdown and its rendered/sanitized HTML (D-44).
    answer = models.TextField()
    answer_html = models.TextField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["qanda", "position"],
                name="unique_qanda_item_position",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.qanda_id}#{self.position}"
