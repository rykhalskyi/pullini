"""Artifact services: slug allocation, rendering and share tokens (E6, D-24/D-31).

The rendered fields are derived from the source Markdown, exactly as the wiki
generator derives them (HLD §8): ``content`` stays authoritative.
"""

from __future__ import annotations

import secrets

from django.db import IntegrityError
from django.db.models import Count
from django.utils.text import slugify

from pullini.artifacts.models import Artifact, Tag, Visibility
from pullini.wiki import markup

_SLUG_MAX = 200
_SHARE_TOKEN_BYTES = 24

MAX_TAGS_PER_ARTIFACT = 20
MAX_TAG_NAME = 50
_TAG_SLUG_MAX = 60


class TagError(ValueError):
    """A tag name or a tag set supplied by the caller is not acceptable."""


def normalize_tag(name: str) -> str:
    """Trim and collapse whitespace; keep the display case; validate length."""
    normalized = " ".join(name.split())
    if not normalized:
        raise TagError("Tag name must not be empty.")
    if len(normalized) > MAX_TAG_NAME:
        raise TagError(f"Tag name must be at most {MAX_TAG_NAME} characters.")
    return normalized


def _tag_slug(name: str) -> str:
    """Case-folded, URL-safe identity for a tag name (D-37)."""
    normalized = normalize_tag(name)
    slug = slugify(normalized, allow_unicode=True)[:_TAG_SLUG_MAX]
    if not slug:
        raise TagError("Tag name must contain letters or numbers.")
    return slug


def _get_or_create_tag(user, name: str, slug: str) -> Tag:
    """Lazily create the tag, keeping the display case of the first writer."""
    try:
        tag, _ = Tag.objects.get_or_create(user=user, slug=slug, defaults={"name": name})
    except IntegrityError:
        tag = Tag.objects.get(user=user, slug=slug)
    return tag


def validate_tags(names) -> list[tuple[str, str]]:
    """Normalize, dedupe and cap tag names, returning ``(slug, display)`` pairs.

    Pure: it never touches the database, so callers can reject bad input before
    mutating anything.
    """
    resolved: dict[str, str] = {}
    for raw in names:
        display = normalize_tag(raw)
        resolved.setdefault(_tag_slug(raw), display)
    if len(resolved) > MAX_TAGS_PER_ARTIFACT:
        raise TagError(f"An artifact can have at most {MAX_TAGS_PER_ARTIFACT} tags.")
    return list(resolved.items())


def resolve_tags(user, names) -> list[Tag]:
    """Return (creating lazily) the unique tags named in ``names`` (D-37)."""
    return [_get_or_create_tag(user, display, slug) for slug, display in validate_tags(names)]


def set_artifact_tags(artifact: Artifact, names) -> list[Tag]:
    """Replace the artifact's tags with exactly ``names``."""
    tags = resolve_tags(artifact.user, names)
    artifact.tags.set(tags)
    return tags


def add_tags(artifact: Artifact, names) -> list[Tag]:
    """Attach the named tags, creating the missing ones, capped per artifact."""
    existing = set(artifact.tags.values_list("slug", flat=True))
    fresh = [(slug, display) for slug, display in validate_tags(names) if slug not in existing]
    if len(existing) + len(fresh) > MAX_TAGS_PER_ARTIFACT:
        raise TagError(f"An artifact can have at most {MAX_TAGS_PER_ARTIFACT} tags.")
    tags = [_get_or_create_tag(artifact.user, display, slug) for slug, display in fresh]
    artifact.tags.add(*tags)
    return tags


def remove_tags(artifact: Artifact, slugs) -> None:
    """Detach the tags identified by ``slugs`` from the artifact."""
    artifact.tags.remove(*artifact.tags.filter(slug__in=list(slugs)))


def delete_tag(user, slug: str) -> bool:
    """Delete a tag from the user's vocabulary (and every artifact using it)."""
    deleted, _ = Tag.objects.filter(user=user, slug=slug).delete()
    return deleted > 0


def tags_with_counts(user):
    """The user's tags annotated with how many artifacts reference each."""
    return Tag.objects.filter(user=user).annotate(count=Count("artifacts")).order_by("name")


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
    tags=None,
) -> Artifact:
    """Create a private artifact with a frozen per-user slug (D-31)."""
    artifact = Artifact(
        user=user,
        title=title,
        slug=allocate_slug(user, title),
        visibility=visibility,
    )
    artifact = save_artifact(artifact, content=content)
    if tags is not None:
        set_artifact_tags(artifact, tags)
    return artifact


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
