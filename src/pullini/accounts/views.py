"""Personal access token management views: ``/settings/tokens/`` (E6, D-23)."""

from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from pullini.accounts.tokens import create_for_user

_NEW_TOKEN_SESSION_KEY = "new_token_secret"
_MAX_EXPIRY_DAYS = 3650


@login_required
def token_list(request: HttpRequest) -> HttpResponse:
    # The freshly created secret is flashed through the session so a reload (or
    # back button) cannot show it again.
    new_secret = request.session.pop(_NEW_TOKEN_SESSION_KEY, None)
    tokens = request.user.access_tokens.all()
    return render(request, "accounts/tokens.html", {"tokens": tokens, "new_secret": new_secret})


@login_required
@require_POST
def token_create(request: HttpRequest) -> HttpResponse:
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Give the token a name.")
        return redirect("accounts:tokens")

    expires_at = None
    raw_days = request.POST.get("expires_in_days", "").strip()
    if raw_days:
        try:
            days = int(raw_days)
        except ValueError:
            days = 0
        if days < 1:
            messages.error(request, "Expiry must be a positive number of days.")
            return redirect("accounts:tokens")
        if days > _MAX_EXPIRY_DAYS:
            messages.error(request, f"Expiry cannot exceed {_MAX_EXPIRY_DAYS} days.")
            return redirect("accounts:tokens")
        expires_at = timezone.now() + timedelta(days=days)

    _, raw_secret = create_for_user(request.user, name, expires_at=expires_at)
    request.session[_NEW_TOKEN_SESSION_KEY] = raw_secret
    messages.success(request, f'Token "{name}" created.')
    return redirect("accounts:tokens")


@login_required
@require_POST
def token_revoke(request: HttpRequest, token_id: int) -> HttpResponse:
    token = get_object_or_404(request.user.access_tokens, pk=token_id)
    if token.is_revoked:
        messages.info(request, f'Token "{token.name}" is already revoked.')
    else:
        token.revoke()
        messages.success(request, f'Token "{token.name}" revoked.')
    return redirect("accounts:tokens")
