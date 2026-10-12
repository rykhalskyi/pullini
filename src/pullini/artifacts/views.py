"""Artifact views: read-only owner list/detail, the public share page and the
HTMX tag controls (E6, T4/T8, D-24/D-38).

Artifact **content** stays API-only (D-24); tags are user metadata, so the web
surface lets their owner attach, detach and delete them (D-38).
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from pullini.artifacts import services
from pullini.artifacts.models import Artifact, Tag, Visibility


def _all_tags(request: HttpRequest):
    return services.tags_with_counts(request.user)


@login_required
def artifact_list(request: HttpRequest) -> HttpResponse:
    artifacts = request.user.artifacts.prefetch_related("tags")
    all_tags = _all_tags(request)

    active_tag = None
    slug = request.GET.get("tag", "").strip()
    if slug:
        active_tag = next((tag for tag in all_tags if tag.slug == slug), None)
        if active_tag is not None:
            artifacts = artifacts.filter(tags__slug=slug).distinct()

    return render(
        request,
        "artifacts/list.html",
        {"artifacts": artifacts, "all_tags": all_tags, "active_tag": active_tag},
    )


@login_required
def artifact_detail(request: HttpRequest, slug: str) -> HttpResponse:
    artifact = get_object_or_404(Artifact, user=request.user, slug=slug)
    share_url = None
    if artifact.is_shared:
        share_url = request.build_absolute_uri(
            reverse("artifacts:shared", kwargs={"share_token": artifact.share_token})
        )
    return render(
        request,
        "artifacts/detail.html",
        {"artifact": artifact, "share_url": share_url, "all_tags": _all_tags(request)},
    )


def artifact_shared(request: HttpRequest, share_token: str) -> HttpResponse:
    artifact = get_object_or_404(
        Artifact,
        share_token=share_token,
        visibility=Visibility.UNLISTED,
    )
    return render(request, "artifacts/shared.html", {"artifact": artifact})


def _tags_response(
    request: HttpRequest, artifact: Artifact, error: str | None = None
) -> HttpResponse:
    """Return the refreshed tag widget for HTMX, otherwise a redirect to detail."""
    if request.headers.get("HX-Request"):
        return render(
            request,
            "artifacts/_tags.html",
            {
                "artifact": artifact,
                "all_tags": _all_tags(request),
                "editable": True,
                "error": error,
            },
        )
    return redirect("artifacts:detail", slug=artifact.slug)


@login_required
@require_POST
def tag_add(request: HttpRequest, slug: str) -> HttpResponse:
    artifact = get_object_or_404(Artifact, user=request.user, slug=slug)
    name = request.POST.get("name", "")
    error = None
    try:
        services.add_tags(artifact, [name])
    except services.TagError as exc:
        error = str(exc)
        messages.error(request, error)
    return _tags_response(request, artifact, error=error)


@login_required
@require_POST
def tag_remove(request: HttpRequest, slug: str, tag: str) -> HttpResponse:
    artifact = get_object_or_404(Artifact, user=request.user, slug=slug)
    services.remove_tags(artifact, [tag])
    return _tags_response(request, artifact)


@login_required
@require_POST
def tag_delete(request: HttpRequest, tag: str) -> HttpResponse:
    tag_obj = get_object_or_404(Tag, user=request.user, slug=tag)
    tag_obj.delete()
    return redirect("artifacts:list")
