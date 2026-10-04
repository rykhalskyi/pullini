"""Generated page metadata.

Git remains the source of truth for content (HLD §13); these rows are a
derived, regenerable representation used for navigation and, later, search.
"""

from __future__ import annotations

from django.db import models

from pullini.projects.models import Project
from pullini.wiki import markup


class Page(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="pages")

    # Path within the configured docs folder, posix, including extension.
    path = models.CharField(max_length=500)
    # URL path: the source path without its extension.
    url_path = models.CharField(max_length=500)
    title = models.CharField(max_length=500)

    content = models.TextField(help_text="Source Markdown.")
    html = models.TextField(help_text="Rendered HTML.")
    plain_text = models.TextField(help_text="Tag-stripped text, indexed by search (E5).")
    content_hash = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["path"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "path"],
                name="unique_page_path_per_project",
            ),
        ]
        indexes = [models.Index(fields=["project", "url_path"])]

    def __str__(self) -> str:
        return f"{self.project.slug}:{self.path}"

    @property
    def depth(self) -> int:
        return self.path.count("/")

    @property
    def has_mermaid(self) -> bool:
        return markup.has_mermaid(self.html)
