"""Project model.

A project represents a Git repository and the documentation folder within it
that Pullini presents as a read-only wiki (HLD §5). Git remains the source of
truth; this model only stores configuration.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

_SCP_LIKE_GIT_URL = re.compile(r"^[\w.-]+@[\w.-]+:[\w./-]+$")
_ALLOWED_SCHEMES = ("http://", "https://", "ssh://", "git://", "file://")

DEFAULT_UPDATE_INTERVAL_MINUTES = 10


def validate_git_url(value: str) -> None:
    """Accept common Git URL forms, including scp-like SSH syntax."""
    if value.startswith(_ALLOWED_SCHEMES) or _SCP_LIKE_GIT_URL.match(value):
        return
    raise ValidationError(
        "Enter a valid Git URL, e.g. https://host/repo.git or git@host:team/repo.git."
    )


class Project(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)

    repo_url = models.CharField(max_length=500, validators=[validate_git_url])
    branch = models.CharField(max_length=200, default="main")
    docs_folder = models.CharField(
        max_length=200,
        default="docs",
        help_text="Path within the repository that contains the documentation.",
    )
    update_interval_minutes = models.PositiveIntegerField(
        default=DEFAULT_UPDATE_INTERVAL_MINUTES,
        validators=[MinValueValidator(1)],
        help_text="How often to synchronize from Git, in minutes.",
    )
    enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def get_absolute_url(self) -> str:
        return reverse("projects:detail", kwargs={"slug": self.slug})

    def clean(self) -> None:
        super().clean()
        self.docs_folder = self.docs_folder.strip().strip("/")

    def _unique_slug(self) -> str:
        base = slugify(self.name) or "project"
        slug = base
        suffix = 2
        existing = Project.objects.exclude(pk=self.pk)
        while existing.filter(slug=slug).exists():
            slug = f"{base}-{suffix}"
            suffix += 1
        return slug

    @property
    def update_interval_display(self) -> str:
        minutes = self.update_interval_minutes
        if minutes % 60 == 0:
            hours = minutes // 60
            return f"every {hours} hour{'s' if hours != 1 else ''}"
        return f"every {minutes} minute{'s' if minutes != 1 else ''}"
