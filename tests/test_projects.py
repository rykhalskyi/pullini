"""Tests for the Project model, URLs, visibility rules and admin access."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from pullini.projects import views
from pullini.projects.models import Project, SyncStatus

pytestmark = pytest.mark.django_db


def make_project(**kwargs) -> Project:
    defaults = {"name": "Payments", "repo_url": "https://git.example.com/payments.git"}
    defaults.update(kwargs)
    return Project.objects.create(**defaults)


def test_defaults_and_slug():
    project = make_project()

    assert project.branch == "main"
    assert project.docs_folder == "docs"
    assert project.update_interval_minutes == 10
    assert project.enabled is True
    assert project.slug == "payments"
    assert str(project) == "Payments"
    assert project.get_absolute_url() == reverse("projects:detail", kwargs={"slug": "payments"})


def test_slug_collision_gets_suffix():
    first = make_project(name="My Docs")
    second = make_project(name="My-Docs")

    assert first.slug == "my-docs"
    assert second.slug == "my-docs-2"


@pytest.mark.parametrize(
    "url",
    [
        "https://git.example.com/payments.git",
        "ssh://git@example.com/team/repo.git",
        "git@github.com:team/repo.git",
        "file:///srv/repo.git",
    ],
)
def test_valid_git_urls(url):
    Project(name="Repo", repo_url=url).full_clean(exclude=["slug"])


@pytest.mark.parametrize("url", ["not a url", "ftp://example.com/repo.git", "javascript:alert(1)"])
def test_invalid_git_urls(url):
    with pytest.raises(ValidationError):
        Project(name="Repo", repo_url=url).full_clean(exclude=["slug"])


def test_docs_folder_is_normalized():
    project = Project(
        name="Repo",
        repo_url="https://git.example.com/payments.git",
        docs_folder="/docs/",
    )

    project.clean()

    assert project.docs_folder == "docs"


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(1, "every 1 minute"), (10, "every 10 minutes"), (60, "every 1 hour"), (120, "every 2 hours")],
)
def test_update_interval_display(minutes, expected):
    assert Project(update_interval_minutes=minutes).update_interval_display == expected


def test_project_list_is_public_and_hides_disabled(client):
    make_project(name="Enabled")
    make_project(name="Disabled", enabled=False)

    response = client.get(reverse("projects:list"))

    assert response.status_code == 200
    assert b"Enabled" in response.content
    assert b"Disabled" not in response.content


def test_enabled_project_detail_is_public(client):
    project = make_project(name="Visible")

    response = client.get(project.get_absolute_url())

    assert response.status_code == 200
    assert project.repo_url.encode() in response.content


def test_disabled_project_is_hidden_from_public(client):
    project = make_project(name="Hidden", enabled=False)

    assert client.get(project.get_absolute_url()).status_code == 404


def test_staff_can_see_disabled_projects(client):
    user = get_user_model().objects.create_user("admin", password="secret", is_staff=True)
    client.force_login(user)
    project = make_project(name="Hidden", enabled=False)

    assert client.get(project.get_absolute_url()).status_code == 200
    assert b"Hidden" in client.get(reverse("projects:list")).content


def test_admin_requires_login(client):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert "/admin/login/" in response.url


def test_admin_changelist_accessible_to_superuser(client):
    user = get_user_model().objects.create_superuser("admin", password="secret")
    client.force_login(user)

    response = client.get("/admin/projects/project/")

    assert response.status_code == 200


class _FakeState:
    status = SyncStatus.OK
    last_error = ""


def test_refresh_button_hidden_from_public(client):
    project = make_project()

    assert b"Refresh now" not in client.get(project.get_absolute_url()).content


def test_refresh_button_visible_to_staff(client):
    user = get_user_model().objects.create_superuser("admin", password="secret")
    client.force_login(user)
    project = make_project()

    assert b"Refresh now" in client.get(project.get_absolute_url()).content


def test_refresh_requires_login(client, monkeypatch):
    project = make_project()
    monkeypatch.setattr(views, "sync_project", lambda *a, **k: pytest.fail("must not sync"))

    response = client.post(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 302
    assert "/admin/login/" in response.url


def test_refresh_forbidden_for_non_staff(client):
    user = get_user_model().objects.create_user("user", password="secret")
    client.force_login(user)
    project = make_project()

    response = client.post(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 403


def test_refresh_rejects_get(client):
    user = get_user_model().objects.create_superuser("admin", password="secret")
    client.force_login(user)
    project = make_project()

    response = client.get(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 405


def test_staff_refresh_triggers_forced_sync(client, monkeypatch):
    user = get_user_model().objects.create_superuser("admin", password="secret")
    client.force_login(user)
    project = make_project()
    calls = []
    monkeypatch.setattr(
        views,
        "sync_project",
        lambda proj, force=False: (calls.append((proj.pk, force)), _FakeState())[1],
    )

    response = client.post(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 302
    assert calls == [(project.pk, True)]


def test_admin_change_form_has_refresh_button(client):
    user = get_user_model().objects.create_superuser("admin", password="secret")
    client.force_login(user)
    project = make_project()

    response = client.get(f"/admin/projects/project/{project.pk}/change/")

    assert response.status_code == 200
    assert b"Refresh now" in response.content
