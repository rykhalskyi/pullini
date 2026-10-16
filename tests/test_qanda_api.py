"""Q&A REST API tests: upsert, reads, owner scoping and validation (E6, T13)."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from pullini.accounts.tokens import create_for_user
from pullini.artifacts import services as artifact_services
from pullini.projects.models import Project
from pullini.qanda.models import QandA
from pullini.wiki.models import Page

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def bearer(user, name: str = "laptop") -> dict[str, str]:
    _, raw = create_for_user(user, name)
    return {"HTTP_AUTHORIZATION": f"Bearer {raw}"}


def post_json(client, url, payload, **headers):
    return client.post(url, data=json.dumps(payload), content_type="application/json", **headers)


def make_project(name: str = "Payments", *, enabled: bool = True, user=None) -> Project:
    return Project.objects.create(
        name=name,
        repo_url="https://git.example.com/payments.git",
        enabled=enabled,
        user=user,
    )


def make_page(project: Project, path: str = "guide/setup.md", **kwargs) -> Page:
    defaults = {
        "url_path": path.rsplit(".", 1)[0],
        "title": path,
        "content": "# Page",
        "html": "<h1>Page</h1>",
        "plain_text": "Page",
        "content_hash": f"hash-{path}",
    }
    defaults.update(kwargs)
    return Page.objects.create(project=project, path=path, **defaults)


def make_artifact(user, title: str = "Report"):
    return artifact_services.create_artifact(user, title=title, content="# A")


def e(question: str = "Q", answer: str = "A"):
    return {"question": question, "answer": answer}


def page_payload(project: Project, path: str = "guide/setup.md", entries=None):
    return {
        "page": {"project": project.slug, "path": path},
        "entries": entries if entries is not None else [e()],
    }


# --- auth ---------------------------------------------------------------------


def test_endpoints_require_a_token(client):
    assert client.get(reverse("api:qanda_collection")).status_code == 401


# --- create / list / detail ---------------------------------------------------


def test_create_page_qanda(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)

    response = post_json(client, reverse("api:qanda_collection"), page_payload(project), **headers)

    assert response.status_code == 201
    body = response.json()
    assert body["target_type"] == "page"
    assert body["target"] == {
        "project": "payments",
        "path": "guide/setup.md",
        "title": "guide/setup.md",
    }
    assert body["item_count"] == 1
    assert body["stale"] is False
    assert body["items"][0]["question"] == "Q"
    assert body["items"][0]["answer"] == "A"
    assert body["items"][0]["answer_html"] == "<p>A</p>"
    assert QandA.objects.filter(user=user).count() == 1


def test_create_replaces_the_existing_qanda(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)
    first = post_json(
        client, reverse("api:qanda_collection"), page_payload(project), **headers
    ).json()

    second = post_json(
        client,
        reverse("api:qanda_collection"),
        page_payload(project, entries=[e("New"), e("Two")]),
        **headers,
    )

    assert second.status_code == 200
    assert second.json()["id"] == first["id"]
    assert second.json()["item_count"] == 2
    assert QandA.objects.filter(user=user).count() == 1


def test_create_artifact_qanda(client):
    user = make_user()
    headers = bearer(user)
    artifact = make_artifact(user)

    response = post_json(
        client,
        reverse("api:qanda_collection"),
        {"artifact": artifact.slug, "entries": [e()]},
        **headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["target_type"] == "artifact"
    assert body["target"] == {"slug": "report", "title": "Report"}


def test_list_is_scoped_to_the_token_owner(client):
    owner = make_user("owner")
    other = make_user("other")
    project = make_project(user=owner)
    make_page(project)
    post_json(client, reverse("api:qanda_collection"), page_payload(project), **bearer(owner))

    listing = client.get(reverse("api:qanda_collection"), **bearer(other)).json()

    assert listing["qanda"] == []


def test_detail_and_delete(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)
    qanda = post_json(
        client, reverse("api:qanda_collection"), page_payload(project), **headers
    ).json()
    url = reverse("api:qanda_item", args=[qanda["id"]])

    detail = client.get(url, **headers)
    assert detail.status_code == 200
    assert detail.json()["items"][0]["answer"] == "A"

    assert client.delete(url, **headers).status_code == 204
    assert client.get(url, **headers).status_code == 404


def test_cross_user_access_returns_404(client):
    owner = make_user("owner")
    other = make_user("other")
    project = make_project(user=owner)
    make_page(project)
    qanda = post_json(
        client, reverse("api:qanda_collection"), page_payload(project), **bearer(owner)
    ).json()

    url = reverse("api:qanda_item", args=[qanda["id"]])
    assert client.get(url, **bearer(other)).status_code == 404
    assert client.delete(url, **bearer(other)).status_code == 404


# --- validation ---------------------------------------------------------------


def test_target_must_be_exactly_one(client):
    headers = bearer(make_user())
    project = make_project()
    make_page(project)
    collection = reverse("api:qanda_collection")

    neither = post_json(client, collection, {"entries": [e()]}, **headers)
    assert neither.status_code == 400
    assert neither.json()["error"] == "invalid_field"

    both = post_json(
        client,
        collection,
        {
            "page": {"project": project.slug, "path": "guide/setup.md"},
            "artifact": "x",
            "entries": [e()],
        },
        **headers,
    )
    assert both.status_code == 400


def test_unknown_target_returns_404(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)

    missing_page = post_json(
        client,
        reverse("api:qanda_collection"),
        {"page": {"project": project.slug, "path": "nope.md"}, "entries": [e()]},
        **headers,
    )
    assert missing_page.status_code == 404

    missing_artifact = post_json(
        client, reverse("api:qanda_collection"), {"artifact": "nope", "entries": [e()]}, **headers
    )
    assert missing_artifact.status_code == 404


def test_invalid_entries_are_a_400(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)

    response = post_json(
        client,
        reverse("api:qanda_collection"),
        page_payload(project, entries=[{"question": "Q", "answer": ""}]),
        **headers,
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_field"


def test_invalid_json_body(client):
    headers = bearer(make_user())

    response = client.post(
        reverse("api:qanda_collection"),
        data="{not json",
        content_type="application/json",
        **headers,
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_json"


def test_disallowed_methods_return_405(client):
    headers = bearer(make_user())

    collection = client.delete(reverse("api:qanda_collection"), **headers)
    assert collection.status_code == 405
    assert collection.json()["error"] == "method_not_allowed"

    item = client.put(reverse("api:qanda_item", args=[1]), **headers)
    assert item.status_code == 405
