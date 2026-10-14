"""Authenticated Q&A REST API (E6, T13/D-43…D-45).

Exposes the T12 Q&A domain so an agent can create/replace, read and delete Q&A
sets. Every resource is scoped to the token owner (D-32); plain Django JSON views,
no DRF (D-25).
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from pullini.accounts.auth import require_token
from pullini.api.http import ApiError, api_endpoint, isoformat, json_body
from pullini.artifacts.models import Artifact
from pullini.projects.access import visible_projects
from pullini.qanda import services
from pullini.qanda.models import QandA
from pullini.wiki.models import Page

# A simple cap instead of pagination (out of scope for v1).
LIST_LIMIT = 200


def _qanda_queryset():
    return QandA.objects.select_related("page", "page__project", "artifact").prefetch_related(
        "items"
    )


def _get_owned_qanda(request: HttpRequest, pk: int) -> QandA:
    return get_object_or_404(_qanda_queryset(), pk=pk, user=request.user)


def _target(qanda: QandA) -> dict:
    if qanda.page_id:
        return {
            "project": qanda.page.project.slug,
            "path": qanda.page.path,
            "title": qanda.page.title,
        }
    return {"slug": qanda.artifact.slug, "title": qanda.artifact.title}


def serialize_qanda_list_item(qanda: QandA) -> dict:
    return {
        "id": qanda.id,
        "target_type": qanda.target_type,
        "target": _target(qanda),
        "item_count": len(qanda.items.all()),
        "stale": qanda.is_stale,
        "created_at": isoformat(qanda.created_at),
        "updated_at": isoformat(qanda.updated_at),
    }


def serialize_qanda_detail(qanda: QandA) -> dict:
    data = serialize_qanda_list_item(qanda)
    data["items"] = [
        {
            "position": item.position,
            "question": item.question,
            "answer": item.answer,
            "answer_html": item.answer_html,
        }
        for item in qanda.items.all()
    ]
    return data


def _resolve_target(request: HttpRequest, data: dict) -> dict:
    """Return the single ``{"page": Page}`` or ``{"artifact": Artifact}`` target."""
    has_page = "page" in data
    has_artifact = "artifact" in data
    if has_page == has_artifact:
        raise ApiError("invalid_field", 'Provide exactly one of "page" or "artifact".')

    if has_page:
        spec = data["page"]
        if not isinstance(spec, dict):
            raise ApiError("invalid_field", '"page" must be an object with "project" and "path".')
        project_slug = spec.get("project")
        path = spec.get("path")
        if not isinstance(project_slug, str) or not project_slug.strip():
            raise ApiError("invalid_field", '"page.project" must be a non-empty string.')
        if not isinstance(path, str) or not path.strip():
            raise ApiError("invalid_field", '"page.path" must be a non-empty string.')
        project = get_object_or_404(visible_projects(request.user), slug=project_slug)
        return {"page": get_object_or_404(Page, project=project, path=path)}

    slug = data["artifact"]
    if not isinstance(slug, str) or not slug.strip():
        raise ApiError("invalid_field", '"artifact" must be a non-empty slug.')
    return {"artifact": get_object_or_404(Artifact, user=request.user, slug=slug)}


@require_token
@api_endpoint
@require_http_methods(["GET", "POST"])
def qanda_collection(request: HttpRequest):
    if request.method == "GET":
        qanda = services.list_qanda(request.user)[:LIST_LIMIT]
        return JsonResponse({"qanda": [serialize_qanda_list_item(set_) for set_ in qanda]})

    data = json_body(request)
    target = _resolve_target(request, data)
    existing = services.get_qanda(request.user, **target)
    try:
        qanda = services.create_qanda(request.user, entries=data.get("entries"), **target)
    except services.QandAError as exc:
        raise ApiError("invalid_field", str(exc)) from exc
    return JsonResponse(serialize_qanda_detail(qanda), status=200 if existing else 201)


@require_token
@api_endpoint
@require_http_methods(["GET", "DELETE"])
def qanda_item(request: HttpRequest, pk: int):
    qanda = _get_owned_qanda(request, pk)
    if request.method == "DELETE":
        qanda.delete()
        return HttpResponse(status=204)
    return JsonResponse(serialize_qanda_detail(qanda))
