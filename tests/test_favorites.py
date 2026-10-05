"""Favorites model, star toggle, list and home-page tests (E6, D-26)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from pullini.favorites.models import Favorite
from pullini.projects.models import Project
from pullini.wiki.models import Page

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def make_project(name: str = "Payments") -> Project:
    return Project.objects.create(name=name, repo_url="https://git.example.com/payments.git")


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


def test_favorite_is_unique_per_user_page():
    user = make_user()
    page = make_page(make_project())
    Favorite.objects.create(user=user, page=page)

    with pytest.raises(IntegrityError), transaction.atomic():
        Favorite.objects.create(user=user, page=page)


def test_toggle_requires_login(client):
    page = make_page(make_project())

    response = client.post(reverse("favorites:toggle", args=[page.pk]))

    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_toggle_rejects_get(client):
    client.force_login(make_user())
    page = make_page(make_project())

    assert client.get(reverse("favorites:toggle", args=[page.pk])).status_code == 405


def test_toggle_adds_and_removes(client):
    user = make_user()
    page = make_page(make_project())
    client.force_login(user)

    first = client.post(reverse("favorites:toggle", args=[page.pk]))
    assert first.status_code == 302
    assert Favorite.objects.filter(user=user, page=page).exists()

    second = client.post(reverse("favorites:toggle", args=[page.pk]))
    assert second.status_code == 302
    assert not Favorite.objects.filter(user=user, page=page).exists()


def test_htmx_toggle_returns_partial(client):
    user = make_user()
    page = make_page(make_project())
    client.force_login(user)

    response = client.post(
        reverse("favorites:toggle", args=[page.pk]),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert b"Favorited" in response.content
    assert f"favorite-star-{page.pk}".encode() in response.content


def test_favorites_list_requires_login(client):
    response = client.get(reverse("favorites:list"))

    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_favorites_list_shows_only_own_favorites(client):
    user = make_user()
    other = make_user("other")
    project = make_project()
    mine = make_page(project, path="mine.md", title="Mine")
    theirs = make_page(project, path="theirs.md", title="Theirs")
    Favorite.objects.create(user=user, page=mine)
    Favorite.objects.create(user=other, page=theirs)
    client.force_login(user)

    content = client.get(reverse("favorites:list")).content

    assert b"Mine" in content
    assert b"Theirs" not in content


def test_home_shows_only_six_most_recent_favorites(client):
    user = make_user()
    project = make_project()
    client.force_login(user)
    pages = [make_page(project, path=f"p{i}.md", title=f"Page {i}") for i in range(7)]
    now = timezone.now()
    for i, page in enumerate(pages):
        favorite = Favorite.objects.create(user=user, page=page)
        Favorite.objects.filter(pk=favorite.pk).update(created_at=now + timedelta(minutes=i))

    content = client.get(reverse("home")).content

    assert b"Page 6" in content
    assert b"Page 1" in content
    assert b"Page 0" not in content


def test_wiki_page_reflects_favorite_state(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    Favorite.objects.create(user=user, page=page)
    client.force_login(user)

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert b"Favorited" in content


def test_wiki_page_shows_unfavorited_star(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    client.force_login(user)

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert b"Favorited" not in content
    assert b"Favorite" in content
