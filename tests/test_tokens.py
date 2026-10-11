"""Personal access token model, service, views and decorator tests (E6, D-23/D-30/D-32)."""

from __future__ import annotations

import re
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from pullini.accounts.auth import require_token
from pullini.accounts.tokens import authenticate, create_for_user, digest, extract_prefix

pytestmark = pytest.mark.django_db

SECRET_RE = re.compile(rb"pln_[0-9a-f]{8}_[A-Za-z0-9_-]{20,}")


def make_user(**kwargs):
    defaults = {"username": "reader", "password": "s3cret-pass"}
    defaults.update(kwargs)
    return get_user_model().objects.create_user(**defaults)


def test_create_for_user_returns_raw_secret_and_stores_only_its_hash():
    user = make_user()

    token, raw = create_for_user(user, "laptop")

    assert raw.startswith("pln_")
    assert token.token_hash == digest(raw)
    assert raw not in token.token_hash
    assert token.prefix == extract_prefix(raw)
    assert token.last_used_at is None


def test_extract_prefix_rejects_malformed_tokens():
    assert extract_prefix("nope") is None
    assert extract_prefix("pln_") is None
    assert extract_prefix("pln_onlyprefix") is None


def test_authenticate_accepts_a_valid_token():
    user = make_user()
    token, raw = create_for_user(user, "laptop")

    assert authenticate(raw) == token


def test_authenticate_rejects_unknown_or_wrong_secret():
    _, raw = create_for_user(make_user(), "laptop")
    other_prefix = raw.split("_", 2)[1]

    assert authenticate(None) is None
    assert authenticate("") is None
    assert authenticate("pln_deadbeef_wrong") is None
    assert authenticate(f"pln_{other_prefix}_tampered") is None


def test_authenticate_rejects_expired_token():
    token, raw = create_for_user(
        make_user(), "laptop", expires_at=timezone.now() - timedelta(minutes=1)
    )

    assert token.is_expired
    assert authenticate(raw) is None


def test_authenticate_rejects_revoked_token():
    token, raw = create_for_user(make_user(), "laptop")
    token.revoke()

    assert token.is_revoked
    assert authenticate(raw) is None


def test_authenticate_rejects_inactive_user():
    user = make_user(username="disabled", is_active=False)
    _, raw = create_for_user(user, "laptop")

    assert authenticate(raw) is None


def test_tokens_page_requires_login(client):
    response = client.get(reverse("accounts:tokens"))

    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_create_requires_login(client):
    response = client.post(reverse("accounts:token_create"), {"name": "laptop"})

    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_create_shows_secret_once(client):
    user = make_user()
    client.force_login(user)

    response = client.post(reverse("accounts:token_create"), {"name": "laptop"}, follow=True)

    assert response.status_code == 200
    assert b"laptop" in response.content
    assert SECRET_RE.search(response.content), "the fresh secret should be shown"
    assert user.access_tokens.count() == 1

    again = client.get(reverse("accounts:tokens"))
    assert b"data-token-secret" not in again.content, "the secret must not be shown again"


def test_create_requires_a_name(client):
    user = make_user()
    client.force_login(user)

    response = client.post(reverse("accounts:token_create"), {"name": "  "}, follow=True)

    assert b"Give the token a name" in response.content
    assert user.access_tokens.count() == 0


def test_create_with_expiry_sets_expires_at(client):
    user = make_user()
    client.force_login(user)

    client.post(reverse("accounts:token_create"), {"name": "laptop", "expires_in_days": "30"})

    token = user.access_tokens.get()
    assert token.expires_at is not None
    assert token.expires_at > timezone.now() + timedelta(days=29)


def test_create_rejects_invalid_expiry(client):
    user = make_user()
    client.force_login(user)

    response = client.post(
        reverse("accounts:token_create"), {"name": "laptop", "expires_in_days": "0"}, follow=True
    )

    assert b"positive number of days" in response.content
    assert user.access_tokens.count() == 0


def test_create_rejects_expiry_beyond_the_cap(client):
    user = make_user()
    client.force_login(user)

    response = client.post(
        reverse("accounts:token_create"),
        {"name": "laptop", "expires_in_days": "9999999999"},
        follow=True,
    )

    assert response.status_code == 200
    assert b"Expiry cannot exceed" in response.content
    assert user.access_tokens.count() == 0


def test_revoke_requires_post_and_login(client):
    user = make_user()
    token, _ = create_for_user(user, "laptop")

    anonymous = client.post(reverse("accounts:token_revoke", args=[token.pk]))
    assert anonymous.status_code == 302
    assert anonymous.url.startswith("/login/")

    client.force_login(user)
    assert client.get(reverse("accounts:token_revoke", args=[token.pk])).status_code == 405


def test_revoke_only_own_tokens(client):
    owner = make_user()
    other = make_user(username="other")
    token, _ = create_for_user(owner, "laptop")
    client.force_login(other)

    response = client.post(reverse("accounts:token_revoke", args=[token.pk]))

    assert response.status_code == 404
    token.refresh_from_db()
    assert not token.is_revoked


def test_revoke_disables_the_token(client):
    user = make_user()
    token, raw = create_for_user(user, "laptop")
    client.force_login(user)

    response = client.post(reverse("accounts:token_revoke", args=[token.pk]), follow=True)

    assert response.status_code == 200
    token.refresh_from_db()
    assert token.is_revoked
    assert authenticate(raw) is None


def test_nav_shows_tokens_for_authenticated_users(client):
    assert b"Tokens" not in client.get(reverse("home")).content

    client.force_login(make_user())

    assert b"Tokens" in client.get(reverse("home")).content


# --- @require_token decorator -------------------------------------------------


def _protected_view(request):
    return JsonResponse({"ok": True, "user": request.user.username})


protected = require_token(_protected_view)


def test_require_token_rejects_missing_header():
    response = protected(RequestFactory().get("/api/"))

    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Bearer"


def test_require_token_accepts_valid_token_and_sets_user():
    user = make_user()
    token, raw = create_for_user(user, "laptop")
    request = RequestFactory().get("/api/", HTTP_AUTHORIZATION=f"Bearer {raw}")

    response = protected(request)

    assert response.status_code == 200
    assert request.user == user
    assert request.token == token
    token.refresh_from_db()
    assert token.last_used_at is not None


def test_require_token_rejects_non_bearer_scheme():
    _, raw = create_for_user(make_user(), "laptop")
    request = RequestFactory().get("/api/", HTTP_AUTHORIZATION=f"Token {raw}")

    assert protected(request).status_code == 401


def test_require_token_rejects_revoked_token():
    token, raw = create_for_user(make_user(), "laptop")
    token.revoke()
    request = RequestFactory().get("/api/", HTTP_AUTHORIZATION=f"Bearer {raw}")

    assert protected(request).status_code == 401


def test_require_token_exempts_the_view_from_csrf():
    assert getattr(protected, "csrf_exempt", False) is True
