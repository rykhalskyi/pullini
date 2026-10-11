"""Small helpers for the JSON artifact API (E6, T5).

Plain Django views, no Django REST Framework (D-25). Views raise
:class:`ApiError` for client mistakes and wrap themselves in :func:`api_endpoint`
so every failure returns the same ``{"error", "detail"}`` payload.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from functools import wraps

from django.http import Http404, HttpRequest, HttpResponseNotAllowed, JsonResponse


class ApiError(Exception):
    """A client error rendered as a JSON response by :func:`api_endpoint`."""

    def __init__(self, code: str, detail: str, status: int = 400) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.status = status


def error(code: str, detail: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": code, "detail": detail}, status=status)


def isoformat(value) -> str | None:
    return value.isoformat() if value else None


def api_endpoint(view: Callable) -> Callable:
    """Render every client mistake from the view as a JSON response.

    Translates :class:`ApiError`, Django's ``Http404`` and the ``405`` produced
    by ``@require_http_methods`` into the shared ``{"error", "detail"}`` payload.
    It must wrap ``@require_http_methods`` so the not-allowed response passes
    through it.
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        try:
            response = view(request, *args, **kwargs)
        except ApiError as exc:
            return error(exc.code, exc.detail, exc.status)
        except Http404 as exc:
            return error("not_found", str(exc) or "Not found.", status=404)
        if isinstance(response, HttpResponseNotAllowed):
            return error("method_not_allowed", "Method not allowed.", status=405)
        return response

    return wrapper


def json_body(request: HttpRequest) -> dict:
    """Return the request body parsed as a JSON object, or raise :class:`ApiError`."""
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ApiError("invalid_json", "Request body must be valid JSON.") from exc
    if not isinstance(data, dict):
        raise ApiError("invalid_json", "Request body must be a JSON object.")
    return data


def require_str(data: dict, key: str, *, allow_empty: bool = False) -> str:
    value = data.get(key)
    if not isinstance(value, str) or (not value.strip() and not allow_empty):
        raise ApiError("invalid_field", f'"{key}" must be a non-empty string.')
    return value
