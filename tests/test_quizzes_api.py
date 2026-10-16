"""Quiz REST API tests: CRUD, attempts, page reads and auth (E6, T10/D-32/D-42)."""

from __future__ import annotations

import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from pullini.accounts.tokens import create_for_user
from pullini.artifacts import services as artifact_services
from pullini.projects.models import Project
from pullini.quizzes.models import Quiz
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


def q(text: str = "Q", options=("a", "b"), correct: int = 0, explanation: str = ""):
    return {
        "text": text,
        "options": list(options),
        "correct_index": correct,
        "explanation": explanation,
    }


def page_payload(project: Project, path: str = "guide/setup.md", questions=None):
    return {
        "page": {"project": project.slug, "path": path},
        "questions": questions if questions is not None else [q()],
    }


# --- auth ---------------------------------------------------------------------


def test_endpoints_require_a_token(client):
    for method, url in (
        ("get", reverse("api:quiz_collection")),
        ("get", reverse("api:page_collection")),
    ):
        assert getattr(client, method)(url).status_code == 401


# --- create / list / detail ---------------------------------------------------


def test_create_page_quiz(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)

    response = post_json(client, reverse("api:quiz_collection"), page_payload(project), **headers)

    assert response.status_code == 201
    body = response.json()
    assert body["target_type"] == "page"
    assert body["target"] == {
        "project": "payments",
        "path": "guide/setup.md",
        "title": "guide/setup.md",
    }
    assert body["question_count"] == 1
    assert body["stale"] is False
    assert body["last_score"] is None
    assert body["questions"][0]["text"] == "Q"
    assert body["questions"][0]["correct_index"] == 0
    assert Quiz.objects.filter(user=user).count() == 1


def test_create_replaces_the_existing_quiz(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)
    first = post_json(
        client, reverse("api:quiz_collection"), page_payload(project), **headers
    ).json()

    second = post_json(
        client,
        reverse("api:quiz_collection"),
        page_payload(project, questions=[q("New"), q("Two")]),
        **headers,
    )

    assert second.status_code == 200
    assert second.json()["id"] == first["id"]
    assert second.json()["question_count"] == 2
    assert Quiz.objects.filter(user=user).count() == 1


def test_create_artifact_quiz(client):
    user = make_user()
    headers = bearer(user)
    artifact = make_artifact(user)

    response = post_json(
        client,
        reverse("api:quiz_collection"),
        {"artifact": artifact.slug, "questions": [q()]},
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
    post_json(client, reverse("api:quiz_collection"), page_payload(project), **bearer(owner))

    listing = client.get(reverse("api:quiz_collection"), **bearer(other)).json()

    assert listing["quizzes"] == []


def test_detail_and_delete(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)
    quiz = post_json(
        client, reverse("api:quiz_collection"), page_payload(project), **headers
    ).json()
    url = reverse("api:quiz_item", args=[quiz["id"]])

    detail = client.get(url, **headers)
    assert detail.status_code == 200
    assert detail.json()["questions"][0]["options"] == ["a", "b"]

    assert client.delete(url, **headers).status_code == 204
    assert client.get(url, **headers).status_code == 404


def test_cross_user_access_returns_404(client):
    owner = make_user("owner")
    other = make_user("other")
    project = make_project(user=owner)
    make_page(project)
    quiz = post_json(
        client, reverse("api:quiz_collection"), page_payload(project), **bearer(owner)
    ).json()

    url = reverse("api:quiz_item", args=[quiz["id"]])
    assert client.get(url, **bearer(other)).status_code == 404
    assert client.delete(url, **bearer(other)).status_code == 404


# --- attempts -----------------------------------------------------------------


def test_attempt_scores_and_persists(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)
    quiz = post_json(
        client,
        reverse("api:quiz_collection"),
        page_payload(project, questions=[q(correct=1, options=("a", "b")), q(correct=0)]),
        **headers,
    ).json()
    url = reverse("api:quiz_attempt", args=[quiz["id"]])

    perfect = post_json(client, url, {"answers": [1, 0]}, **headers)
    assert perfect.status_code == 200
    body = perfect.json()
    assert body["score"] == 2
    assert body["total"] == 2
    assert body["best_score"] == 2
    assert body["results"][0]["is_correct"] is True

    partial = post_json(client, url, {"answers": [0, 1]}, **headers).json()
    assert partial["score"] == 0
    assert partial["last_score"] == 0
    assert partial["best_score"] == 2


def test_attempt_requires_an_answers_list(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)
    quiz = post_json(
        client, reverse("api:quiz_collection"), page_payload(project), **headers
    ).json()

    response = post_json(client, reverse("api:quiz_attempt", args=[quiz["id"]]), {}, **headers)

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_field"


def test_attempt_is_owner_scoped(client):
    owner = make_user("owner")
    other = make_user("other")
    project = make_project(user=owner)
    make_page(project)
    quiz = post_json(
        client, reverse("api:quiz_collection"), page_payload(project), **bearer(owner)
    ).json()

    response = post_json(
        client, reverse("api:quiz_attempt", args=[quiz["id"]]), {"answers": [0]}, **bearer(other)
    )

    assert response.status_code == 404


# --- validation ---------------------------------------------------------------


def test_target_must_be_exactly_one(client):
    headers = bearer(make_user())
    project = make_project()
    make_page(project)
    collection = reverse("api:quiz_collection")

    neither = post_json(client, collection, {"questions": [q()]}, **headers)
    assert neither.status_code == 400
    assert neither.json()["error"] == "invalid_field"

    both = post_json(
        client,
        collection,
        {
            "page": {"project": project.slug, "path": "guide/setup.md"},
            "artifact": "x",
            "questions": [q()],
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
        reverse("api:quiz_collection"),
        {"page": {"project": project.slug, "path": "nope.md"}, "questions": [q()]},
        **headers,
    )
    assert missing_page.status_code == 404

    missing_artifact = post_json(
        client, reverse("api:quiz_collection"), {"artifact": "nope", "questions": [q()]}, **headers
    )
    assert missing_artifact.status_code == 404


def test_invalid_questions_are_a_400(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project)

    response = post_json(
        client,
        reverse("api:quiz_collection"),
        page_payload(project, questions=[{"text": "Q", "options": ["only"], "correct_index": 0}]),
        **headers,
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_field"


def test_invalid_json_body(client):
    headers = bearer(make_user())

    response = client.post(
        reverse("api:quiz_collection"),
        data="{not json",
        content_type="application/json",
        **headers,
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_json"


def test_disallowed_methods_return_405(client):
    headers = bearer(make_user())

    collection = client.delete(reverse("api:quiz_collection"), **headers)
    assert collection.status_code == 405
    assert collection.json()["error"] == "method_not_allowed"

    attempts = client.get(reverse("api:quiz_attempt", args=[1]), **headers)
    assert attempts.status_code == 405


# --- page reads ---------------------------------------------------------------


def test_pages_list_and_filter(client):
    user = make_user()
    headers = bearer(user)
    payments = make_project("Payments", user=user)
    billing = make_project("Billing", user=user)
    make_page(payments, path="guide/setup.md", title="Setup")
    make_page(payments, path="index.md", title="Home")
    make_page(billing, path="intro.md", title="Intro")

    all_pages = client.get(reverse("api:page_collection"), **headers).json()["pages"]
    assert {page["title"] for page in all_pages} == {"Setup", "Home", "Intro"}

    filtered = client.get(reverse("api:page_collection"), {"project": "billing"}, **headers).json()[
        "pages"
    ]
    assert [page["title"] for page in filtered] == ["Intro"]


def test_page_item_returns_source(client):
    user = make_user()
    headers = bearer(user)
    project = make_project(user=user)
    make_page(project, path="guide/setup.md", title="Setup", content="# Setup\n\nHello.")

    body = client.get(
        reverse("api:page_item", args=[project.slug, "guide/setup.md"]), **headers
    ).json()

    assert body["project"] == "payments"
    assert body["path"] == "guide/setup.md"
    assert body["title"] == "Setup"
    assert body["content"] == "# Setup\n\nHello."


def test_other_users_projects_are_not_readable(client):
    user = make_user()
    other = make_user("other")
    headers = bearer(user)
    project = make_project(user=other)
    make_page(project)

    listing = client.get(reverse("api:page_collection"), **headers).json()
    assert listing["pages"] == []

    response = client.get(
        reverse("api:page_item", args=[project.slug, "guide/setup.md"]), **headers
    )
    assert response.status_code == 404


def test_unknown_page_is_a_json_404(client):
    user = make_user()
    project = make_project(user=user)

    response = client.get(
        reverse("api:page_item", args=[project.slug, "missing.md"]), **bearer(user)
    )

    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
