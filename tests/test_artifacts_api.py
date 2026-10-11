"""Artifact REST API tests: CRUD, isolation, sharing and auth (E6, T5/D-25/D-32)."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from pullini.accounts.tokens import create_for_user
from pullini.artifacts.models import Artifact, Visibility

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def bearer(user, name: str = "laptop", **kwargs) -> dict[str, str]:
    _, raw = create_for_user(user, name, **kwargs)
    return {"HTTP_AUTHORIZATION": f"Bearer {raw}"}


def post_json(client, url, payload, **headers):
    return client.post(url, data=json.dumps(payload), content_type="application/json", **headers)


def put_json(client, url, payload, **headers):
    return client.put(url, data=json.dumps(payload), content_type="application/json", **headers)


def patch_json(client, url, payload, **headers):
    return client.patch(url, data=json.dumps(payload), content_type="application/json", **headers)


# --- auth ---------------------------------------------------------------------


def test_me_requires_a_token(client):
    response = client.get(reverse("api:me"))

    assert response.status_code == 401


def test_me_returns_user_and_token_metadata(client):
    user = make_user()
    headers = bearer(user, "claude")

    payload = client.get(reverse("api:me"), **headers).json()

    assert payload["username"] == "reader"
    assert payload["token"]["name"] == "claude"
    assert payload["token"]["prefix"]
    assert payload["token"]["expires_at"] is None
    assert payload["token"]["last_used_at"] is not None


def test_expired_or_revoked_tokens_are_rejected(client):
    user = make_user()
    expired = bearer(user, "expired", expires_at=timezone.now() - timedelta(minutes=1))
    revoked_user = make_user("revoked")
    token, raw = create_for_user(revoked_user, "laptop")
    token.revoke()

    assert client.get(reverse("api:me"), **expired).status_code == 401
    assert client.get(reverse("api:me"), HTTP_AUTHORIZATION=f"Bearer {raw}").status_code == 401


# --- crud ---------------------------------------------------------------------


def test_create_list_and_get(client):
    user = make_user()
    headers = bearer(user)

    created = post_json(
        client,
        reverse("api:artifact_collection"),
        {"title": "Weekly Report", "content": "# Hello"},
        **headers,
    )

    assert created.status_code == 201
    body = created.json()
    assert body["slug"] == "weekly-report"
    assert body["visibility"] == "private"
    assert body["share_url"] is None
    assert "<h1" in body["html"]
    assert body["plain_text"] == "Hello"

    listing = client.get(reverse("api:artifact_collection"), **headers).json()
    assert [item["slug"] for item in listing["artifacts"]] == ["weekly-report"]

    detail = client.get(reverse("api:artifact_item", args=["weekly-report"]), **headers).json()
    assert detail["content"] == "# Hello"


def test_list_is_scoped_to_the_token_owner(client):
    owner = make_user("owner")
    other = make_user("other")
    owner_headers = bearer(owner)
    other_headers = bearer(other)
    post_json(
        client,
        reverse("api:artifact_collection"),
        {"title": "Mine", "content": ""},
        **owner_headers,
    )

    listing = client.get(reverse("api:artifact_collection"), **other_headers).json()

    assert listing["artifacts"] == []


def test_update_keeps_slug_frozen(client):
    user = make_user()
    headers = bearer(user)
    post_json(
        client, reverse("api:artifact_collection"), {"title": "Old", "content": "# A"}, **headers
    )

    response = put_json(
        client,
        reverse("api:artifact_item", args=["old"]),
        {"title": "Renamed", "content": "# B"},
        **headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Renamed"
    assert body["slug"] == "old"
    assert body["plain_text"] == "B"


def test_patch_updates_only_provided_fields(client):
    user = make_user()
    headers = bearer(user)
    post_json(
        client,
        reverse("api:artifact_collection"),
        {"title": "Title", "content": "# Body"},
        **headers,
    )
    url = reverse("api:artifact_item", args=["title"])

    title_only = patch_json(client, url, {"title": "New Title"}, **headers).json()
    assert title_only["title"] == "New Title"
    assert title_only["content"] == "# Body"

    content_only = patch_json(client, url, {"content": "# Changed"}, **headers).json()
    assert content_only["title"] == "New Title"
    assert content_only["content"] == "# Changed"


def test_delete_removes_the_artifact(client):
    user = make_user()
    headers = bearer(user)
    post_json(
        client, reverse("api:artifact_collection"), {"title": "Gone", "content": ""}, **headers
    )

    response = client.delete(reverse("api:artifact_item", args=["gone"]), **headers)

    assert response.status_code == 204
    assert not Artifact.objects.filter(slug="gone").exists()


def test_cross_user_access_returns_404(client):
    owner = make_user("owner")
    other = make_user("other")
    post_json(
        client,
        reverse("api:artifact_collection"),
        {"title": "Secret", "content": "# Secret"},
        **bearer(owner),
    )
    url = reverse("api:artifact_item", args=["secret"])

    headers = bearer(other)
    assert client.get(url, **headers).status_code == 404
    assert client.delete(url, **headers).status_code == 404


def test_not_found_is_a_json_error(client):
    headers = bearer(make_user())

    response = client.get(reverse("api:artifact_item", args=["missing"]), **headers)

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


# --- sharing ------------------------------------------------------------------


def test_share_enable_and_revoke(client):
    user = make_user()
    headers = bearer(user)
    post_json(
        client,
        reverse("api:artifact_collection"),
        {"title": "Report", "content": "# A"},
        **headers,
    )
    url = reverse("api:artifact_share", args=["report"])

    enabled = client.post(url, **headers).json()
    assert enabled["visibility"] == "unlisted"
    assert "/a/" in enabled["share_url"]

    revoked = client.delete(url, **headers)
    assert revoked.status_code == 204
    refreshed = client.get(reverse("api:artifact_item", args=["report"]), **headers).json()
    assert refreshed["visibility"] == "private"
    assert refreshed["share_url"] is None


def test_create_as_unlisted_returns_a_share_url(client):
    user = make_user()
    headers = bearer(user)

    body = post_json(
        client,
        reverse("api:artifact_collection"),
        {"title": "Report", "content": "# A", "visibility": "unlisted"},
        **headers,
    ).json()

    assert body["visibility"] == Visibility.UNLISTED
    assert "/a/" in body["share_url"]


# --- validation ---------------------------------------------------------------


def test_invalid_json_body_is_a_400(client):
    headers = bearer(make_user())

    response = client.post(
        reverse("api:artifact_collection"),
        data="{not json",
        content_type="application/json",
        **headers,
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_json"


def test_missing_required_fields_are_a_400(client):
    headers = bearer(make_user())

    response = post_json(client, reverse("api:artifact_collection"), {"title": "  "}, **headers)

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_field"


def test_disallowed_methods_return_405(client):
    headers = bearer(make_user())

    collection = client.delete(reverse("api:artifact_collection"), **headers)
    assert collection.status_code == 405
    assert collection.json()["error"] == "method_not_allowed"

    me = client.post(reverse("api:me"), content_type="application/json", **headers)
    assert me.status_code == 405
    assert me.json()["error"] == "method_not_allowed"


# --- agent skill --------------------------------------------------------------


def test_skill_requires_a_token(client):
    assert client.get(reverse("api:skill")).status_code == 401


def test_skill_returns_the_authoring_guide(client):
    response = client.get(reverse("api:skill"), **bearer(make_user()))

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/markdown")
    body = response.content
    assert b"name: pullini-artifacts" in body
    assert b"POST   /api/artifacts/" in body
    assert b"DELETE /api/artifacts/<slug>/" in body
