"""Artifact services: slug allocation, rendering and share tokens (E6, D-24/D-31).

The rendered fields are derived from the source Markdown, exactly as the wiki
generator derives them (HLD §8): ``content`` stays authoritative.
"""

from __future__ import annotations

import secrets

from django.utils.text import slugify

from pullini.artifacts.models import Artifact, Visibility
from pullini.wiki import markup

_SLUG_MAX = 200
_SHARE_TOKEN_BYTES = 24


def allocate_slug(user, title: str, *, exclude_pk=None) -> str:
    """Return a slug unique within ``user``'s artifacts."""
    base = slugify(title)[:_SLUG_MAX] or "artifact"
    slug = base
    suffix = 2
    existing = Artifact.objects.filter(user=user).exclude(pk=exclude_pk)
    while existing.filter(slug=slug).exists():
        tail = f"-{suffix}"
        slug = f"{base[: _SLUG_MAX - len(tail)]}{tail}"
        suffix += 1
    return slug


def save_artifact(artifact: Artifact, *, content: str) -> Artifact:
    """Render ``content`` into the derived fields and persist the artifact."""
    artifact.content = content
    artifact.html = markup.render(content)
    artifact.plain_text = markup.to_plain_text(artifact.html)
    artifact.content_hash = markup.content_hash(content)
    artifact.save()
    return artifact


def create_artifact(
    user,
    *,
    title: str,
    content: str,
    visibility: str = Visibility.PRIVATE,
) -> Artifact:
    """Create a private artifact with a frozen per-user slug (D-31)."""
    artifact = Artifact(
        user=user,
        title=title,
        slug=allocate_slug(user, title),
        visibility=visibility,
    )
    return save_artifact(artifact, content=content)


def generate_share_token(artifact: Artifact) -> str:
    """Mark the artifact unlisted and return its share token (idempotent)."""
    if not artifact.share_token:
        artifact.share_token = secrets.token_urlsafe(_SHARE_TOKEN_BYTES)
        artifact.visibility = Visibility.UNLISTED
        artifact.save(update_fields=["share_token", "visibility", "updated_at"])
    return artifact.share_token


def clear_share_token(artifact: Artifact) -> None:
    """Revoke the share link and return the artifact to private."""
    if artifact.share_token or artifact.visibility != Visibility.PRIVATE:
        artifact.share_token = None
        artifact.visibility = Visibility.PRIVATE
        artifact.save(update_fields=["share_token", "visibility", "updated_at"])
