"""Admin invite links and the public password setup flow."""

from __future__ import annotations

import re
from urllib.parse import urlparse

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse

from pullini.accounts.invites import build_password_setup_url

pytestmark = pytest.mark.django_db

SETUP_URL_RE = re.compile(rb'value="(http://testserver/accounts/set-password/[^"]+)"')


def make_user(**kwargs):
    defaults = {"username": "reader", "password": "s3cret-pass"}
    defaults.update(kwargs)
    return get_user_model().objects.create_user(**defaults)


def make_admin():
    return get_user_model().objects.create_superuser("root", password="s3cret-pass")


def make_invited_user(username: str = "newbie"):
    user = get_user_model().objects.create_user(username=username)
    user.set_unusable_password()
    user.save(update_fields=["password"])
    return user


def setup_path(user) -> str:
    request = RequestFactory().get("/")
    return urlparse(build_password_setup_url(request, user)).path


def test_admin_add_form_only_asks_for_a_username(client):
    client.force_login(make_admin())

    response = client.get(reverse("admin:auth_user_add"))

    assert response.status_code == 200
    assert b'name="username"' in response.content
    assert b'name="password1"' not in response.content
    assert b'name="password2"' not in response.content


def test_adding_a_user_issues_a_one_time_setup_link(client):
    client.force_login(make_admin())

    response = client.post(
        reverse("admin:auth_user_add"),
        {"username": "newbie"},
        follow=True,
    )

    assert response.status_code == 200
    user = get_user_model().objects.get(username="newbie")
    assert not user.has_usable_password()

    match = SETUP_URL_RE.search(response.content)
    assert match, "the admin should see the generated setup link"
    assert b"Password setup link" in response.content

    reloaded = client.get(reverse("admin:auth_user_change", args=[user.pk]))
    assert b"Password setup link" not in reloaded.content
    assert SETUP_URL_RE.search(reloaded.content) is None


def test_invited_user_cannot_log_in_before_setting_a_password(client):
    make_invited_user()

    response = client.post(reverse("login"), {"username": "newbie", "password": "anything"})

    assert response.status_code == 200
    assert not client.session.get("_auth_user_id")


def test_setup_link_sets_the_password_and_redirects_to_login(client):
    user = make_invited_user()
    path = setup_path(user)

    form_page = client.get(path)
    assert form_page.status_code == 200
    assert b"Set your password" in form_page.content

    response = client.post(
        path,
        {
            "new_password1": "correct-horse-battery-staple-97",
            "new_password2": "correct-horse-battery-staple-97",
        },
    )

    assert response.status_code == 302
    assert response.url == reverse("login")
    user.refresh_from_db()
    assert user.check_password("correct-horse-battery-staple-97")

    login = client.post(
        reverse("login"),
        {"username": "newbie", "password": "correct-horse-battery-staple-97"},
    )
    assert login.status_code == 302
    assert client.session.get("_auth_user_id")

    reused = client.get(path)
    assert b"This link is invalid" in reused.content


def test_weak_passwords_are_rejected(client):
    user = make_invited_user()
    path = setup_path(user)

    response = client.post(path, {"new_password1": "123", "new_password2": "123"})

    assert response.status_code == 200
    user.refresh_from_db()
    assert not user.has_usable_password()


def test_expired_setup_link_is_rejected(client, settings):
    user = make_invited_user()
    path = setup_path(user)
    settings.PASSWORD_RESET_TIMEOUT = -1

    response = client.get(path)

    assert b"This link is invalid" in response.content


def test_malformed_or_tampered_setup_links_are_rejected(client):
    user = make_invited_user()
    valid_path = setup_path(user)

    malformed = client.get(reverse("password_setup", args=["not-a-uid", "not-a-token"]))
    assert b"This link is invalid" in malformed.content

    tampered = client.get(reverse("password_setup", args=[valid_path.split("/")[3], "bad-token"]))
    assert b"This link is invalid" in tampered.content


def test_inactive_users_cannot_use_a_setup_link(client):
    user = make_invited_user()
    path = setup_path(user)
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.get(path)

    assert b"This link is invalid" in response.content


def test_changing_email_does_not_invalidate_the_link(client):
    user = make_invited_user()
    path = setup_path(user)
    user.email = "new@example.com"
    user.save(update_fields=["email"])

    response = client.get(path)

    assert response.status_code == 200
    assert b"Set your password" in response.content


def test_admin_reset_removes_password_and_issues_a_new_link(client):
    admin = make_admin()
    client.force_login(admin)
    user = make_invited_user()
    old_path = setup_path(user)
    assert b"Set your password" in client.get(old_path).content

    response = client.post(
        reverse("admin:auth_user_setup_link", args=[user.pk]),
        follow=True,
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert not user.has_usable_password()
    assert b"This link is invalid" in client.get(old_path).content

    match = SETUP_URL_RE.search(response.content)
    assert match, "a fresh setup link should be shown after reset"
    new_path = urlparse(match.group(1).decode()).path
    assert new_path != old_path
    assert b"Set your password" in client.get(new_path).content


def test_admin_reset_removes_an_existing_password(client):
    admin = make_admin()
    client.force_login(admin)
    user = make_user(username="existing")

    client.post(reverse("admin:auth_user_setup_link", args=[user.pk]))

    user.refresh_from_db()
    assert not user.has_usable_password()


def test_admin_reset_requires_post(client):
    admin = make_admin()
    user = make_user(username="existing")
    url = reverse("admin:auth_user_setup_link", args=[user.pk])

    client.force_login(admin)

    assert client.get(url).status_code == 405


def test_non_superuser_staff_cannot_reset_passwords(client):
    user = make_user(username="existing")
    url = reverse("admin:auth_user_setup_link", args=[user.pk])
    staff = make_user(username="staff", is_staff=True)

    client.force_login(staff)
    response = client.post(url)

    assert response.status_code == 302
    assert "/admin/login/" in response.url
    user.refresh_from_db()
    assert user.has_usable_password()


def test_admin_reset_signs_out_existing_sessions(client):
    admin = make_admin()
    client.force_login(admin)
    user = make_user(username="existing")
    user_client = Client()
    user_client.force_login(user)
    assert user_client.get(reverse("accounts:tokens")).status_code == 200

    client.post(reverse("admin:auth_user_setup_link", args=[user.pk]))

    response = user_client.get(reverse("accounts:tokens"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_save_and_add_another_keeps_the_link_for_the_user_page(client):
    client.force_login(make_admin())

    response = client.post(
        reverse("admin:auth_user_add"),
        {"username": "newbie", "_addanother": "Save and add another"},
        follow=True,
    )

    assert response.status_code == 200
    assert b'name="username"' in response.content
    assert b"Password setup link" not in response.content

    user = get_user_model().objects.get(username="newbie")
    page = client.get(reverse("admin:auth_user_change", args=[user.pk]))
    assert SETUP_URL_RE.search(page.content)


def test_setup_link_is_not_shown_on_another_users_page(client):
    client.force_login(make_admin())
    other = make_user(username="other")

    response = client.post(reverse("admin:auth_user_add"), {"username": "newbie"})
    assert response.status_code == 302
    user = get_user_model().objects.get(username="newbie")

    wrong_page = client.get(reverse("admin:auth_user_change", args=[other.pk]))
    assert b"Password setup link" not in wrong_page.content

    right_page = client.get(reverse("admin:auth_user_change", args=[user.pk]))
    assert SETUP_URL_RE.search(right_page.content)


def test_admin_add_form_rejects_duplicate_username_case_insensitively(client):
    client.force_login(make_admin())
    make_user(username="Reader")

    response = client.post(reverse("admin:auth_user_add"), {"username": "reader"})

    assert response.status_code == 200
    assert not get_user_model().objects.filter(username="reader").exists()


def test_setup_link_shows_the_configured_expiry(client, settings):
    client.force_login(make_admin())
    settings.PASSWORD_RESET_TIMEOUT = 7200

    response = client.post(reverse("admin:auth_user_add"), {"username": "newbie"}, follow=True)

    assert b"Password setup link" in response.content
    assert b"2 hours" in response.content


def test_setup_page_is_not_cached_and_marks_passwords_sensitive(client):
    user = make_invited_user()

    response = client.get(setup_path(user))

    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"]
    assert response.wsgi_request.sensitive_post_parameters == (
        "new_password1",
        "new_password2",
    )
