"""Token-authenticated account endpoint: ``GET /api/me/`` (E6, T5)."""

from __future__ import annotations

from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_http_methods

from pullini.accounts.auth import require_token
from pullini.api.http import isoformat


@require_token
@require_http_methods(["GET"])
def me(request: HttpRequest) -> JsonResponse:
    token = request.token
    return JsonResponse(
        {
            "username": request.user.get_username(),
            "token": {
                "name": token.name,
                "prefix": token.prefix,
                "created_at": isoformat(token.created_at),
                "expires_at": isoformat(token.expires_at),
                "last_used_at": isoformat(token.last_used_at),
            },
        }
    )
