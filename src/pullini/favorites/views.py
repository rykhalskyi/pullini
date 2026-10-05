"""Favorites views: the user's list and the HTMX star toggle (E6, D-26)."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from pullini.favorites.models import Favorite
from pullini.projects.access import visible_projects
from pullini.wiki.models import Page


def _next_url(request: HttpRequest) -> str:
    """Return a safe redirect target from the POST body or the referer."""
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return reverse("favorites:list")


@login_required
def favorites_list(request: HttpRequest) -> HttpResponse:
    favorites = (
        Favorite.objects.filter(
            user=request.user,
            page__project__in=visible_projects(request.user),
        )
        .select_related("page", "page__project")
        .order_by("-created_at")
    )
    return render(request, "favorites/list.html", {"favorites": favorites})


@login_required
@require_POST
def favorite_toggle(request: HttpRequest, page_id: int) -> HttpResponse:
    page = get_object_or_404(
        Page,
        pk=page_id,
        project__in=visible_projects(request.user),
    )
    favorite, created = Favorite.objects.get_or_create(user=request.user, page=page)
    if not created:
        favorite.delete()

    if request.headers.get("HX-Request"):
        return render(
            request,
            "favorites/_star.html",
            {"page": page, "is_favorite": created, "next": _next_url(request)},
        )
    return redirect(_next_url(request))
