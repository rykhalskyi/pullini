"""Read-only artifact views: owner list/detail and the public share page (E6, D-24)."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from pullini.artifacts.models import Artifact, Visibility


@login_required
def artifact_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "artifacts/list.html",
        {"artifacts": request.user.artifacts.all()},
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
        {"artifact": artifact, "share_url": share_url},
    )


def artifact_shared(request: HttpRequest, share_token: str) -> HttpResponse:
    artifact = get_object_or_404(
        Artifact,
        share_token=share_token,
        visibility=Visibility.UNLISTED,
    )
    return render(request, "artifacts/shared.html", {"artifact": artifact})
