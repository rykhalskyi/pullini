"""Authenticated artifact REST API (E6, T5).

The API is the only way to mutate artifacts (D-24) and every resource is scoped
to the token's owner (D-32). Plain Django JSON views, no DRF (D-25).
"""

from __future__ import annotations

from importlib.resources import files

from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from pullini.accounts.auth import require_token
from pullini.api.http import (
    ApiError,
    api_endpoint,
    isoformat,
    json_body,
    parse_str_list,
    require_str,
)
from pullini.artifacts import services
from pullini.artifacts.models import Artifact, Visibility

# A simple cap instead of pagination (out of scope for v1).
LIST_LIMIT = 200

_SKILL_FILE = files("pullini.artifacts").joinpath("skill.md")


def _share_url(request: HttpRequest, artifact: Artifact) -> str | None:
    if not artifact.share_token:
        return None
    return request.build_absolute_uri(reverse("artifacts:shared", args=[artifact.share_token]))


def serialize_list_item(request: HttpRequest, artifact: Artifact) -> dict:
    return {
        "slug": artifact.slug,
        "title": artifact.title,
        "visibility": artifact.visibility,
        "share_url": _share_url(request, artifact),
        "tags": [tag.name for tag in artifact.tags.all()],
        "created_at": isoformat(artifact.created_at),
        "updated_at": isoformat(artifact.updated_at),
    }


def serialize_detail(request: HttpRequest, artifact: Artifact) -> dict:
    data = serialize_list_item(request, artifact)
    data.update(
        {
            "content": artifact.content,
            "html": artifact.html,
            "plain_text": artifact.plain_text,
        }
    )
    return data


def _get_owned(request: HttpRequest, slug: str) -> Artifact:
    return get_object_or_404(Artifact, user=request.user, slug=slug)


def _visibility_from(data: dict) -> str:
    visibility = data.get("visibility", Visibility.PRIVATE)
    if visibility not in Visibility.values:
        raise ApiError("invalid_field", '"visibility" must be "private" or "unlisted".')
    return visibility


@require_token
@api_endpoint
@require_http_methods(["GET", "POST"])
def artifact_collection(request: HttpRequest):
    if request.method == "GET":
        artifacts = request.user.artifacts.all()
        tag_slug = request.GET.get("tag", "").strip()
        if tag_slug:
            artifacts = artifacts.filter(tags__user=request.user, tags__slug=tag_slug)
        artifacts = artifacts.prefetch_related("tags").distinct()[:LIST_LIMIT]
        return JsonResponse(
            {"artifacts": [serialize_list_item(request, artifact) for artifact in artifacts]}
        )

    data = json_body(request)
    title = require_str(data, "title")
    content = require_str(data, "content", allow_empty=True)
    visibility = _visibility_from(data)
    tags = parse_str_list(data, "tags")
    try:
        artifact = services.create_artifact(
            request.user, title=title, content=content, visibility=visibility, tags=tags
        )
    except services.TagError as exc:
        raise ApiError("invalid_field", str(exc)) from exc
    if visibility == Visibility.UNLISTED:
        services.generate_share_token(artifact)
    return JsonResponse(serialize_detail(request, artifact), status=201)


@require_token
@api_endpoint
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
def artifact_item(request: HttpRequest, slug: str):
    artifact = _get_owned(request, slug)

    if request.method == "GET":
        return JsonResponse(serialize_detail(request, artifact))

    if request.method == "DELETE":
        artifact.delete()
        return HttpResponse(status=204)

    data = json_body(request)
    title: str | None = None
    content: str | None = None
    tags = parse_str_list(data, "tags")
    if request.method == "PUT":
        title = require_str(data, "title")
        content = require_str(data, "content", allow_empty=True)
    else:  # PATCH
        if "title" in data:
            title = require_str(data, "title")
        if "content" in data:
            content = require_str(data, "content", allow_empty=True)
        if title is None and content is None and tags is None:
            raise ApiError("invalid_field", 'Provide "title", "content" and/or "tags".')

    if tags is not None:
        try:
            services.validate_tags(tags)  # reject bad input before mutating
        except services.TagError as exc:
            raise ApiError("invalid_field", str(exc)) from exc

    if title is not None:
        artifact.title = title
    if content is not None:
        services.save_artifact(artifact, content=content)
    elif title is not None:
        artifact.save(update_fields=["title", "updated_at"])
    if tags is not None:
        services.set_artifact_tags(artifact, tags)
        artifact.save(update_fields=["updated_at"])
    return JsonResponse(serialize_detail(request, artifact))


@require_token
@api_endpoint
@require_http_methods(["POST", "DELETE"])
def artifact_share(request: HttpRequest, slug: str):
    artifact = _get_owned(request, slug)
    if request.method == "POST":
        services.generate_share_token(artifact)
        return JsonResponse(serialize_detail(request, artifact))
    services.clear_share_token(artifact)
    return HttpResponse(status=204)


@require_token
@api_endpoint
@require_http_methods(["GET"])
def tag_collection(request: HttpRequest):
    """The token owner's tag vocabulary with per-tag artifact counts (D-37)."""
    tags = services.tags_with_counts(request.user)
    return JsonResponse(
        {"tags": [{"name": tag.name, "slug": tag.slug, "count": tag.count} for tag in tags]}
    )


@require_token
@api_endpoint
@require_http_methods(["DELETE"])
def tag_item(request: HttpRequest, slug: str):
    """Delete one tag from the owner's vocabulary (``DELETE /api/tags/<slug>/``)."""
    if not services.delete_tag(request.user, slug):
        raise Http404("Not found.")
    return HttpResponse(status=204)


@require_token
@api_endpoint
@require_http_methods(["GET"])
def skill(request: HttpRequest) -> HttpResponse:
    """Serve the agent skill describing how to use the artifact API."""
    return HttpResponse(
        _SKILL_FILE.read_text(encoding="utf-8"),
        content_type="text/markdown; charset=utf-8",
    )
