"""Tests for the Pullini HTTP client (E6, T6)."""

from __future__ import annotations

import httpx
import pytest

from pullini_mcp.client import Config, PulliniClient, PulliniError


def make_client(handler) -> PulliniClient:
    config = Config(base_url="https://pullini.test", token="pln_test_secret")
    return PulliniClient(config, transport=httpx.MockTransport(handler))


def json_response(status: int, payload) -> httpx.Response:
    return httpx.Response(status, json=payload)


# --- config -------------------------------------------------------------------


def test_from_env_requires_both_variables():
    with pytest.raises(PulliniError, match="PULLINI_URL"):
        Config.from_env({})
    with pytest.raises(PulliniError, match="PULLINI_TOKEN"):
        Config.from_env({"PULLINI_URL": "https://pullini.test"})


def test_from_env_trims_and_strips_trailing_slash():
    config = Config.from_env(
        {"PULLINI_URL": " https://pullini.test/ ", "PULLINI_TOKEN": " pln_x_y "}
    )

    assert config.base_url == "https://pullini.test"
    assert config.token == "pln_x_y"


# --- requests -----------------------------------------------------------------


def test_requests_send_bearer_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["path"] = request.url.path
        return json_response(200, {"username": "reader", "token": {"name": "laptop"}})

    payload = make_client(handler).me()

    assert payload["username"] == "reader"
    assert seen["auth"] == "Bearer pln_test_secret"
    assert seen["path"] == "/api/me/"


def test_skill_returns_markdown_text():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        return httpx.Response(200, text="# Skill\n", headers={"Content-Type": "text/markdown"})

    text = make_client(handler).skill()

    assert text == "# Skill\n"
    assert captured["path"] == "/api/skill/"


def test_create_sends_title_content_and_visibility():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["body"] = request.read().decode()
        return json_response(201, {"slug": "notes", "title": "Notes"})

    artifact = make_client(handler).create_artifact("Notes", "# Notes", "unlisted")

    assert artifact["slug"] == "notes"
    assert captured["method"] == "POST"
    assert '"visibility":"unlisted"' in captured["body"].replace(" ", "")


def test_list_unwraps_artifacts_mapping():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(200, {"artifacts": [{"slug": "a"}, {"slug": "b"}]})

    assert [a["slug"] for a in make_client(handler).list_artifacts()] == ["a", "b"]


def test_update_requires_a_field_before_requesting():
    client = make_client(lambda request: json_response(200, {}))

    with pytest.raises(PulliniError, match="title and/or content"):
        client.update_artifact("notes")


def test_update_patches_only_provided_fields():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["body"] = request.read().decode()
        return json_response(200, {"slug": "notes", "title": "New"})

    make_client(handler).update_artifact("notes", title="New")

    assert captured["method"] == "PATCH"
    assert captured["body"] == '{"title":"New"}'


def test_delete_returns_none_on_204():
    client = make_client(lambda request: httpx.Response(204))

    assert client.delete_artifact("notes") is None


def test_share_enable_posts_and_revoke_deletes():
    methods = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if request.method == "DELETE":
            return httpx.Response(204)
        return json_response(200, {"slug": "notes", "share_url": "https://x/a/t/"})

    client = make_client(handler)
    shared = client.share_artifact("notes")
    client.share_artifact("notes", enable=False)

    assert shared["share_url"] == "https://x/a/t/"
    assert methods == ["POST", "DELETE"]


# --- errors -------------------------------------------------------------------


def test_api_error_maps_detail_and_code():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(400, {"error": "invalid_field", "detail": "title is required"})

    with pytest.raises(PulliniError, match="400 invalid_field: title is required"):
        make_client(handler).create_artifact("", "")


def test_401_error_mentions_the_token():
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(401, {"error": "invalid_token", "detail": "A valid bearer token"})

    with pytest.raises(PulliniError, match="PULLINI_TOKEN"):
        make_client(handler).me()


def test_transport_errors_are_readable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with pytest.raises(PulliniError, match="Could not reach Pullini"):
        make_client(handler).me()
