"""Authenticated artifact REST API (E6, T5).

The API is the only way to mutate artifacts (D-24) and every resource is scoped
to the token's owner (D-32). Plain Django JSON views, no DRF (D-25).
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from pullini.accounts.auth import require_token
from pullini.api.http import ApiError, api_endpoint, isoformat, json_body, require_str
from pullini.artifacts import services
from pullini.artifacts.models import Artifact, Visibility

# A simple cap instead of pagination (out of scope for v1).
LIST_LIMIT = 200


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
@require_http_methods(["GET", "POST"])
@api_endpoint
def artifact_collection(request: HttpRequest):
    if request.method == "GET":
        artifacts = request.user.artifacts.all()[:LIST_LIMIT]
        return JsonResponse(
            {"artifacts": [serialize_list_item(request, artifact) for artifact in artifacts]}
        )

    data = json_body(request)
    title = require_str(data, "title")
    content = require_str(data, "content", allow_empty=True)
    visibility = _visibility_from(data)

    artifact = services.create_artifact(request.user, title=title, content=content)
    if visibility == Visibility.UNLISTED:
        services.generate_share_token(artifact)
    return JsonResponse(serialize_detail(request, artifact), status=201)


@require_token
@require_http_methods(["GET", "PUT", "PATCH", "DELETE"])
@api_endpoint
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
    if request.method == "PUT":
        title = require_str(data, "title")
        content = require_str(data, "content", allow_empty=True)
    else:  # PATCH
        if "title" in data:
            title = require_str(data, "title")
        if "content" in data:
            content = require_str(data, "content", allow_empty=True)
        if title is None and content is None:
            raise ApiError("invalid_field", 'Provide "title" and/or "content".')

    if title is not None:
        artifact.title = title
    if content is not None:
        services.save_artifact(artifact, content=content)
    else:
        artifact.save(update_fields=["title", "updated_at"])
    return JsonResponse(serialize_detail(request, artifact))


@require_token
@require_http_methods(["POST", "DELETE"])
@api_endpoint
def artifact_share(request: HttpRequest, slug: str):
    artifact = _get_owned(request, slug)
    if request.method == "POST":
        services.generate_share_token(artifact)
        return JsonResponse(serialize_detail(request, artifact))
    services.clear_share_token(artifact)
    return HttpResponse(status=204)
