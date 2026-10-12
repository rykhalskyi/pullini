"""Search tests (HLD §9)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.urls import reverse

from pullini.artifacts import services as artifact_services
from pullini.projects.sync import sync_project
from pullini.search.backends import SimpleSearchBackend, get_backend, make_snippet

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def test_search_finds_page_by_content(client, project, remote_repo):
    remote_repo.write("docs/guide/setup.md", "# Setup\n\nInstall the widget with pip.\n")
    sync_project(project, force=True)

    response = client.get(reverse("search:global"), {"q": "widget"})

    assert response.status_code == 200
    assert b"Setup" in response.content


def test_search_finds_page_by_title(client, project):
    sync_project(project, force=True)

    response = client.get(reverse("search:global"), {"q": "Home"})

    assert b"1 result" in response.content
    assert b"/projects/payments/wiki/index/" in response.content


def test_search_matches_page_path(client, project, remote_repo):
    # "zebra" appears only in the path, not the title or body.
    remote_repo.write("docs/guide/zebra.md", "# Overview\n\nHello.\n")
    sync_project(project, force=True)

    response = client.get(reverse("search:global"), {"q": "zebra"})

    assert b"Overview" in response.content


def test_search_matches_project_name(client, project):
    sync_project(project, force=True)

    response = client.get(reverse("search:global"), {"q": "Payments"})

    assert b"1 result" in response.content


def test_search_excludes_disabled_projects(client, project):
    sync_project(project, force=True)
    project.enabled = False
    project.save()

    response = client.get(reverse("search:global"), {"q": "Home"})

    assert b"No results matched" in response.content


def test_scoped_search_returns_results(client, project):
    sync_project(project, force=True)

    response = client.get(reverse("search:project", args=[project.slug]), {"q": "Home"})

    assert response.status_code == 200
    assert b"1 result" in response.content


def test_scoped_search_hidden_for_disabled_project(client, project):
    project.enabled = False
    project.save()

    response = client.get(reverse("search:project", args=[project.slug]))

    assert response.status_code == 404


def test_empty_query_renders_form(client):
    response = client.get(reverse("search:global"))

    assert response.status_code == 200
    assert b"Search all projects" in response.content


def test_header_has_search_form(client):
    body = client.get(reverse("home")).content

    assert b'action="/search/"' in body
    assert b'name="q"' in body


def test_backend_is_engine_appropriate():
    backend = get_backend()

    assert backend.name in {"simple", "postgres"}
    if connection.vendor == "sqlite":
        assert isinstance(backend, SimpleSearchBackend)
        assert backend.name == "simple"


def test_snippet_centers_on_match():
    snippet = make_snippet("a" * 500 + " needle " + "b" * 500, ["needle"])

    assert "needle" in snippet
    assert len(snippet) < 400


@pytest.mark.skipif(connection.vendor != "postgresql", reason="PostgreSQL only")
def test_postgres_full_text_search(client, project, remote_repo):
    remote_repo.write("docs/guide.md", "# Guide\n\nThe zanzibar protocol is documented here.\n")
    sync_project(project, force=True)

    response = client.get(reverse("search:global"), {"q": "zanzibar"})

    assert b"Guide" in response.content


def test_search_finds_own_artifact(client):
    user = make_user()
    artifact_services.create_artifact(
        user, title="Widget Report", content="# Widget Report\n\nThe widget is ready."
    )
    client.force_login(user)

    response = client.get(reverse("search:global"), {"q": "widget"})

    assert response.status_code == 200
    assert b"Widget Report" in response.content
    assert b"Artifact" in response.content


def test_search_matches_artifact_tag(client):
    user = make_user()
    artifact_services.create_artifact(user, title="Report", content="# Report", tags=["zebra"])
    client.force_login(user)

    response = client.get(reverse("search:global"), {"q": "zebra"})

    assert b"Report" in response.content


def test_search_hides_other_users_artifacts(client):
    owner = make_user("owner")
    other = make_user("other")
    artifact_services.create_artifact(
        other, title="Secret Widget", content="# Secret Widget\n\nThe widget is hidden."
    )
    client.force_login(owner)

    response = client.get(reverse("search:global"), {"q": "widget"})

    assert b"Secret Widget" not in response.content


def test_search_artifacts_require_login(client):
    owner = make_user()
    artifact_services.create_artifact(owner, title="Widget Report", content="# Widget Report")

    response = client.get(reverse("search:global"), {"q": "widget"})

    assert b"Widget Report" not in response.content


def test_search_lists_artifacts_before_pages(client, project, remote_repo):
    remote_repo.write("docs/guide/widgethub.md", "# Widgethub\n\nwidget widget\n")
    sync_project(project, force=True)
    user = make_user()
    artifact_services.create_artifact(
        user, title="Widget Notes", content="# Widget Notes\n\nwidget"
    )
    client.force_login(user)

    response = client.get(reverse("search:global"), {"q": "widget"})

    assert response.content.index(b"Widget Notes") < response.content.index(b"Widgethub")


def test_scoped_search_excludes_artifacts(client, project, remote_repo):
    sync_project(project, force=True)
    user = make_user()
    artifact_services.create_artifact(user, title="Widget Notes", content="# Widget Notes")
    client.force_login(user)

    response = client.get(reverse("search:project", args=[project.slug]), {"q": "widget"})

    assert b"Widget Notes" not in response.content
