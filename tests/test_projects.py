"""Tests for the Project model, URLs, owner-private visibility, management and admin access."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from pullini.projects import views
from pullini.projects.models import Project, SyncStatus

pytestmark = pytest.mark.django_db

User = get_user_model()


def make_user(username: str = "owner", **kwargs):
    return User.objects.create_user(username=username, password="s3cret-pass", **kwargs)


def make_project(user=None, **kwargs) -> Project:
    defaults = {
        "name": "Payments",
        "repo_url": "https://git.example.com/payments.git",
        "user": user,
    }
    defaults.update(kwargs)
    return Project.objects.create(**defaults)


class _FakeState:
    status = SyncStatus.OK
    last_error = ""


class _ErrorState:
    status = SyncStatus.ERROR
    last_error = "boom"


def test_defaults_and_slug():
    project = make_project()

    assert project.branch == "main"
    assert project.docs_folder == "docs"
    assert project.update_interval_minutes == 480
    assert project.enabled is True
    assert project.slug == "payments"
    assert str(project) == "Payments"
    assert project.get_absolute_url() == reverse("projects:detail", kwargs={"slug": "payments"})


def test_display_url_masks_embedded_credentials():
    project = Project(
        name="Private",
        repo_url="https://user:s3cret@git.example.com/team/repo.git",
    )

    assert project.display_url == "https://***@git.example.com/team/repo.git"
    assert "s3cret" not in project.display_url


def test_display_url_leaves_scp_like_urls_unchanged():
    project = Project(name="Repo", repo_url="git@github.com:team/repo.git")

    assert project.display_url == "git@github.com:team/repo.git"


def test_project_page_hides_embedded_credentials(client):
    user = make_user()
    project = make_project(
        user=user,
        name="Private",
        repo_url="https://user:s3cret@git.example.com/private.git",
    )
    client.force_login(user)

    response = client.get(project.get_absolute_url())

    assert b"s3cret" not in response.content
    assert b"***@git.example.com" in response.content


def test_slug_collision_gets_suffix():
    user = make_user()
    first = make_project(user=user, name="My Docs", repo_url="https://git.example.com/a.git")
    second = make_project(user=user, name="My-Docs", repo_url="https://git.example.com/b.git")

    assert first.slug == "my-docs"
    assert second.slug == "my-docs-2"


def test_slug_is_globally_unique_across_owners():
    first = make_project(user=make_user("a"), name="Docs")
    second = make_project(user=make_user("b"), name="Docs")

    assert first.slug == "docs"
    assert second.slug == "docs-2"


def test_reserved_slug_is_avoided():
    project = make_project(user=make_user(), name="Manage")

    assert project.slug == "manage-project"


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


# --- owner-private visibility -------------------------------------------------


def test_owner_sees_own_project_in_list(client):
    owner = make_user("owner")
    other = make_user("other")
    make_project(user=owner, name="Mine")
    make_project(user=other, name="Theirs")
    client.force_login(owner)

    content = client.get(reverse("projects:list")).content

    assert b"Mine" in content
    assert b"Theirs" not in content


def test_anonymous_sees_no_projects(client):
    make_project(user=make_user(), name="Mine")

    response = client.get(reverse("projects:list"))

    assert response.status_code == 200
    assert b"Mine" not in response.content


def test_owner_sees_project_detail(client):
    owner = make_user("owner")
    project = make_project(user=owner, name="Visible")
    client.force_login(owner)

    response = client.get(project.get_absolute_url())

    assert response.status_code == 200
    assert project.repo_url.encode() in response.content


def test_other_users_project_is_hidden(client):
    project = make_project(user=make_user("owner"), name="Hidden")
    client.force_login(make_user("other"))

    assert client.get(project.get_absolute_url()).status_code == 404


def test_anonymous_project_detail_is_404(client):
    project = make_project(user=make_user("owner"), name="Hidden")

    assert client.get(project.get_absolute_url()).status_code == 404


def test_superuser_sees_every_project(client):
    project = make_project(user=make_user("owner"), name="Hidden")
    admin = make_user("admin", is_superuser=True)
    client.force_login(admin)

    assert client.get(project.get_absolute_url()).status_code == 200
    assert b"Hidden" in client.get(reverse("projects:list")).content


def test_admin_requires_login(client):
    response = client.get("/admin/")

    assert response.status_code == 302
    assert "/admin/login/" in response.url


def test_admin_changelist_accessible_to_superuser(client):
    user = User.objects.create_superuser("admin", password="secret")
    client.force_login(user)

    response = client.get("/admin/projects/project/")

    assert response.status_code == 200


# --- management page ----------------------------------------------------------


def test_manage_requires_login(client):
    response = client.get(reverse("projects:manage"))

    assert response.status_code == 302
    assert "/login/" in response.url


def test_manage_lists_own_projects_only(client):
    owner = make_user("owner")
    make_project(user=owner, name="Mine")
    make_project(user=make_user("other"), name="Theirs")
    client.force_login(owner)

    content = client.get(reverse("projects:manage")).content

    assert b"Mine" in content
    assert b"Theirs" not in content


def test_manage_redirects_superuser_to_admin(client):
    admin = make_user("admin", is_superuser=True)
    client.force_login(admin)

    response = client.get(reverse("projects:manage"))

    assert response.status_code == 302
    assert response.url == reverse("admin:projects_project_changelist")


def test_create_redirects_superuser_to_admin(client, monkeypatch):
    admin = make_user("admin", is_superuser=True)
    client.force_login(admin)
    monkeypatch.setattr(views, "sync_project", lambda *a, **k: pytest.fail("must not sync"))

    response = client.post(reverse("projects:create"), {"name": "X"})

    assert response.status_code == 302
    assert response.url == reverse("admin:projects_project_changelist")
    assert not Project.objects.filter(name="X").exists()


def test_create_assigns_owner_and_syncs(client, monkeypatch):
    owner = make_user()
    client.force_login(owner)
    calls = []
    monkeypatch.setattr(
        views,
        "sync_project",
        lambda proj, force=False: (calls.append((proj.pk, force)), _FakeState())[1],
    )

    response = client.post(
        reverse("projects:create"),
        {
            "name": "New Docs",
            "repo_url": "https://git.example.com/new.git",
            "branch": "main",
            "docs_folder": "docs",
            "update_interval_minutes": 10,
            "enabled": "on",
        },
    )

    assert response.status_code == 302
    project = Project.objects.get(name="New Docs")
    assert project.user == owner
    assert calls == [(project.pk, True)]


def test_create_tolerates_failed_first_sync(client, monkeypatch):
    owner = make_user()
    client.force_login(owner)
    monkeypatch.setattr(views, "sync_project", lambda proj, force=False: _ErrorState())

    response = client.post(
        reverse("projects:create"),
        {
            "name": "New Docs",
            "repo_url": "https://git.example.com/new.git",
            "branch": "main",
            "docs_folder": "docs",
            "update_interval_minutes": 10,
            "enabled": "on",
        },
    )

    assert response.status_code == 302
    assert Project.objects.filter(user=owner, name="New Docs").exists()


def test_create_rejects_duplicate_name_for_owner(client):
    owner = make_user()
    make_project(user=owner, name="Payments")
    client.force_login(owner)

    response = client.post(
        reverse("projects:create"),
        {
            "name": "Payments",
            "repo_url": "https://git.example.com/other.git",
            "branch": "main",
            "docs_folder": "docs",
            "update_interval_minutes": 10,
            "enabled": "on",
        },
    )

    assert response.status_code == 400
    assert Project.objects.filter(user=owner, name="Payments").count() == 1


def test_create_rejects_duplicate_source_for_owner(client):
    owner = make_user()
    make_project(user=owner, name="Payments")
    client.force_login(owner)

    response = client.post(
        reverse("projects:create"),
        {
            "name": "Payments mirror",
            "repo_url": "https://git.example.com/payments.git",
            "branch": "main",
            "docs_folder": "docs",
            "update_interval_minutes": 480,
            "enabled": "on",
        },
    )

    assert response.status_code == 400
    assert Project.objects.filter(user=owner).count() == 1


def test_two_users_may_track_the_same_repository():
    first = make_project(user=make_user("a"), name="Payments")
    second = make_project(user=make_user("b"), name="Payments")

    assert first.repo_url == second.repo_url
    assert first.slug != second.slug


def test_delete_removes_own_project(client):
    owner = make_user()
    project = make_project(user=owner)
    client.force_login(owner)

    response = client.post(reverse("projects:delete", args=[project.slug]))

    assert response.status_code == 302
    assert not Project.objects.filter(pk=project.pk).exists()


def test_delete_forbidden_for_other_user(client):
    project = make_project(user=make_user("owner"))
    client.force_login(make_user("other"))

    response = client.post(reverse("projects:delete", args=[project.slug]))

    assert response.status_code == 404
    assert Project.objects.filter(pk=project.pk).exists()


def test_delete_redirects_superuser_to_admin(client):
    project = make_project(user=make_user("owner"), name="Visible")
    admin = make_user("admin", is_superuser=True)
    client.force_login(admin)

    response = client.post(reverse("projects:delete", args=[project.slug]))

    assert response.status_code == 302
    assert response.url == reverse("admin:projects_project_changelist")
    assert Project.objects.filter(pk=project.pk).exists()


# --- refresh ------------------------------------------------------------------


def test_refresh_button_hidden_from_anonymous(client):
    project = make_project(user=make_user())

    assert b"Refresh now" not in client.get(project.get_absolute_url()).content


def test_refresh_button_shown_to_owner(client):
    owner = make_user()
    project = make_project(user=owner)
    client.force_login(owner)

    assert b"Refresh now" in client.get(project.get_absolute_url()).content


def test_superuser_does_not_get_in_app_refresh(client):
    project = make_project(user=make_user("owner"), name="Visible")
    admin = make_user("admin", is_superuser=True)
    client.force_login(admin)

    assert b"Refresh now" not in client.get(project.get_absolute_url()).content


def test_refresh_redirects_superuser_to_admin(client, monkeypatch):
    project = make_project(user=make_user("owner"), name="Visible")
    admin = make_user("admin", is_superuser=True)
    client.force_login(admin)
    monkeypatch.setattr(views, "sync_project", lambda *a, **k: pytest.fail("must not sync"))

    response = client.post(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 302
    assert response.url == reverse("admin:projects_project_changelist")


def test_refresh_requires_login(client, monkeypatch):
    project = make_project(user=make_user())
    monkeypatch.setattr(views, "sync_project", lambda *a, **k: pytest.fail("must not sync"))

    response = client.post(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 302
    assert "/login/" in response.url


def test_refresh_not_found_for_non_owner(client):
    project = make_project(user=make_user("owner"))
    client.force_login(make_user("other"))

    response = client.post(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 404


def test_refresh_rejects_get(client):
    user = User.objects.create_superuser("admin", password="secret")
    client.force_login(user)
    project = make_project(user=user)

    response = client.get(reverse("projects:refresh", args=[project.slug]))

    assert response.status_code == 405


def test_owner_refresh_triggers_forced_sync(client, monkeypatch):
    owner = make_user()
    client.force_login(owner)
    project = make_project(user=owner)
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
    user = User.objects.create_superuser("admin", password="secret")
    client.force_login(user)
    project = make_project(user=user)

    response = client.get(f"/admin/projects/project/{project.pk}/change/")

    assert response.status_code == 200
    assert b"Refresh now" in response.content
