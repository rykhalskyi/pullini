"""Reader login/logout and header navigation tests (E6, D-27)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

pytestmark = pytest.mark.django_db


def make_user(**kwargs):
    defaults = {"username": "reader", "password": "s3cret-pass"}
    defaults.update(kwargs)
    return get_user_model().objects.create_user(**defaults)


def test_login_page_renders(client):
    response = client.get(reverse("login"))

    assert response.status_code == 200
    assert b"Log in" in response.content


def test_login_authenticates_and_redirects_home(client):
    make_user()

    response = client.post(reverse("login"), {"username": "reader", "password": "s3cret-pass"})

    assert response.status_code == 302
    assert response.url == "/"
    assert client.session.get("_auth_user_id")


def test_login_honours_next(client):
    make_user()

    response = client.post(
        reverse("login"),
        {"username": "reader", "password": "s3cret-pass", "next": "/favorites/"},
    )

    assert response.url == "/favorites/"


def test_login_rejects_bad_credentials(client):
    make_user()

    response = client.post(reverse("login"), {"username": "reader", "password": "wrong"})

    assert response.status_code == 200
    assert not client.session.get("_auth_user_id")


def test_logout_requires_post(client):
    client.force_login(make_user())

    assert client.get(reverse("logout")).status_code == 405


def test_logout_clears_session(client):
    client.force_login(make_user())

    response = client.post(reverse("logout"))

    assert response.status_code == 302
    assert response.url == "/"
    assert not client.session.get("_auth_user_id")


def test_nav_shows_login_for_anonymous(client):
    content = client.get(reverse("home")).content

    assert b"Log in" in content
    assert b"Log out" not in content
    assert b"Settings" not in content


def test_nav_shows_username_and_logout_for_reader(client):
    client.force_login(make_user())

    content = client.get(reverse("home")).content

    assert b"reader" in content
    assert b"Log out" in content
    assert b"Settings" not in content


def test_nav_shows_settings_for_staff(client):
    client.force_login(make_user(username="admin", is_staff=True))

    assert b"Settings" in client.get(reverse("home")).content
