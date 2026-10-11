"""User-owned Markdown artifacts (E6, D-24).

An artifact is AI-generated Markdown owned by a user and rendered read-only
through the same pipeline as the wiki. Mutations (create/update/delete/share)
arrive through the artifact REST API (T5); the web surface only lists and shows
them. Private by default, with an optional unlisted share link.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.urls import reverse

from pullini.wiki import markup


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    UNLISTED = "unlisted", "Unlisted"


class Artifact(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="artifacts",
    )

    title = models.CharField(max_length=300)
    # Unique per user and frozen at creation (D-31) so URLs and API addresses
    # stay stable when the title changes.
    slug = models.SlugField(max_length=200)

    content = models.TextField(help_text="Source Markdown.")
    html = models.TextField(help_text="Rendered HTML.")
    plain_text = models.TextField(help_text="Tag-stripped text.")
    content_hash = models.CharField(max_length=64)

    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    # Set only while an unlisted share link is active; null otherwise.
    share_token = models.CharField(max_length=64, unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "slug"],
                name="unique_artifact_slug_per_user",
            ),
        ]
        indexes = [models.Index(fields=["user", "-updated_at"])]

    def __str__(self) -> str:
        return f"{self.user}:{self.slug}"

    def get_absolute_url(self) -> str:
        return reverse("artifacts:detail", kwargs={"slug": self.slug})

    @property
    def is_shared(self) -> bool:
        return bool(self.share_token)

    @property
    def has_mermaid(self) -> bool:
        return markup.has_mermaid(self.html)
