"""Thin HTTP client over the Pullini artifact REST API (E6, T6).

The connector runs on the agent's machine and talks to the Pullini host with a
personal access token sent as a bearer header (D-25). This module owns all HTTP
concerns so :mod:`pullini_mcp.server` only maps MCP tool calls to methods and
turns :class:`PulliniError` into a readable tool failure.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

DEFAULT_TIMEOUT = 30.0


class PulliniError(Exception):
    """A readable error for a transport failure or a non-2xx API response."""


@dataclass(frozen=True)
class Config:
    """Connection settings read from the environment (``PULLINI_URL``/``PULLINI_TOKEN``)."""

    base_url: str
    token: str
    timeout: float = DEFAULT_TIMEOUT

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Config:
        """Build a config from ``PULLINI_URL`` and ``PULLINI_TOKEN``."""
        source = os.environ if env is None else env
        base_url = (source.get("PULLINI_URL") or "").strip().rstrip("/")
        token = (source.get("PULLINI_TOKEN") or "").strip()
        if not base_url:
            raise PulliniError(
                "PULLINI_URL is not set. Point it at your Pullini host, e.g. "
                "https://pullini.example.com."
            )
        if not token:
            raise PulliniError(
                "PULLINI_TOKEN is not set. Create a token at /settings/tokens/ and "
                "pass the raw secret."
            )
        return cls(base_url=base_url, token=token)


class PulliniClient:
    """Minimal client for the endpoints that back the artifact API."""

    def __init__(self, config: Config, *, transport: httpx.BaseTransport | None = None) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.token}",
                "Accept": "application/json",
            },
            timeout=config.timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PulliniClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # --- transport -----------------------------------------------------------

    def _send(self, method: str, path: str, *, json: dict | None = None) -> httpx.Response:
        try:
            response = self._client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise PulliniError(
                f"Could not reach Pullini at {self._config.base_url}: {exc}"
            ) from exc
        if response.status_code >= 400:
            raise self._error(response)
        return response

    def _request(self, method: str, path: str, *, json: dict | None = None) -> Any:
        response = self._send(method, path, json=json)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def _error(self, response: httpx.Response) -> PulliniError:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        code = payload.get("error")
        detail = payload.get("detail") or response.reason_phrase or "Request failed."
        message = (
            f"{response.status_code} {code}: {detail}"
            if code
            else f"{response.status_code}: {detail}"
        )
        if response.status_code == 401:
            message += " Check that PULLINI_TOKEN is valid and not expired or revoked."
        if response.status_code == 404:
            message += " The artifact may not exist or may belong to another user."
        return PulliniError(message)

    # --- endpoints -----------------------------------------------------------

    def me(self) -> dict:
        """Return the token owner and token metadata (``GET /api/me/``)."""
        return self._request("GET", "/api/me/")

    def skill(self) -> str:
        """Return the agent skill Markdown (``GET /api/skill/``)."""
        return self._send("GET", "/api/skill/").text

    def list_artifacts(self) -> list[dict]:
        """Return the token owner's artifacts (``GET /api/artifacts/``)."""
        payload = self._request("GET", "/api/artifacts/")
        return payload.get("artifacts", [])

    def get_artifact(self, slug: str) -> dict:
        """Return one artifact with source Markdown and rendered HTML."""
        return self._request("GET", f"/api/artifacts/{quote(slug)}/")

    def create_artifact(self, title: str, content: str, visibility: str = "private") -> dict:
        """Create an artifact (``POST /api/artifacts/``)."""
        return self._request(
            "POST",
            "/api/artifacts/",
            json={"title": title, "content": content, "visibility": visibility},
        )

    def update_artifact(
        self, slug: str, *, title: str | None = None, content: str | None = None
    ) -> dict:
        """Partially update an artifact (``PATCH /api/artifacts/<slug>/``)."""
        if title is None and content is None:
            raise PulliniError("Provide a new title and/or content to update.")
        body: dict[str, str] = {}
        if title is not None:
            body["title"] = title
        if content is not None:
            body["content"] = content
        return self._request("PATCH", f"/api/artifacts/{quote(slug)}/", json=body)

    def delete_artifact(self, slug: str) -> None:
        """Delete an artifact (``DELETE /api/artifacts/<slug>/``)."""
        self._request("DELETE", f"/api/artifacts/{quote(slug)}/")

    def share_artifact(self, slug: str, *, enable: bool = True) -> dict | None:
        """Enable or revoke the unlisted share link (``POST``/``DELETE .../share/``)."""
        method = "POST" if enable else "DELETE"
        return self._request(method, f"/api/artifacts/{quote(slug)}/share/")
