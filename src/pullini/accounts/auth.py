"""``@require_token``: authenticate API requests with a bearer PAT (E6, D-32)."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from pullini.accounts.tokens import authenticate, touch_last_used

_BEARER = "Bearer "


def _bearer_secret(request: HttpRequest) -> str | None:
    header = request.headers.get("Authorization", "")
    if not header.startswith(_BEARER):
        return None
    secret = header[len(_BEARER) :].strip()
    return secret or None


def require_token(view: Callable) -> Callable:
    """Reject requests without a valid ``Authorization: Bearer`` token with a 401.

    On success the view sees ``request.user`` (the token owner) and
    ``request.token``.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        secret = _bearer_secret(request)
        token = authenticate(secret)
        if token is None:
            response = JsonResponse(
                {"error": "invalid_token", "detail": "A valid bearer token is required."},
                status=401,
            )
            response["WWW-Authenticate"] = "Bearer"
            return response
        touch_last_used(token)
        request.user = token.user
        request.token = token
        return view(request, *args, **kwargs)

    # Bearer tokens are not ambient credentials, so CSRF does not apply; exempting
    # the view lets non-browser agents issue unsafe requests (D-32).
    return csrf_exempt(wrapper)
