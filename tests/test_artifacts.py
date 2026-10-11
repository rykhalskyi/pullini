"""Artifact model, service, rendering and view tests (E6, D-24/D-31)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from pullini.artifacts import services
from pullini.artifacts.models import Visibility

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def test_slug_is_frozen_and_unique_per_user():
    user = make_user()

    first = services.create_artifact(user, title="Weekly Report", content="# One")
    second = services.create_artifact(user, title="Weekly Report", content="# Two")
    first.title = "Renamed"
    first.save()

    assert first.slug == "weekly-report"
    assert second.slug == "weekly-report-2"
    first.refresh_from_db()
    assert first.slug == "weekly-report"


def test_slugs_are_scoped_per_user():
    owner = make_user("owner")
    other = make_user("other")

    a = services.create_artifact(owner, title="Report", content="# A")
    b = services.create_artifact(other, title="Report", content="# B")

    assert a.slug == b.slug == "report"


def test_save_renders_html_plain_text_and_hash():
    user = make_user()

    artifact = services.create_artifact(
        user,
        title="Report",
        content="# Title\n\nSome **bold** text.",
    )

    assert "<h1" in artifact.html
    assert "Title" in artifact.html
    assert "<strong>bold</strong>" in artifact.html
    assert artifact.plain_text == "Title Some bold text."
    assert artifact.content_hash
    assert artifact.visibility == Visibility.PRIVATE
    assert artifact.share_token is None


def test_rendered_html_is_sanitized():
    user = make_user()

    artifact = services.create_artifact(
        user,
        title="Report",
        content="<script>alert(1)</script>\n\nSafe",
    )

    assert "<script" not in artifact.html
    assert "Safe" in artifact.html


def test_mermaid_is_detected():
    user = make_user()

    mermaid = services.create_artifact(
        user,
        title="Diagram",
        content="```mermaid\ngraph TD; A-->B;\n```",
    )
    plain = services.create_artifact(user, title="Plain", content="# Just text")

    assert mermaid.has_mermaid
    assert not plain.has_mermaid


def test_generate_and_clear_share_token():
    user = make_user()
    artifact = services.create_artifact(user, title="Report", content="# A")

    token = services.generate_share_token(artifact)

    assert token
    assert artifact.visibility == Visibility.UNLISTED
    assert artifact.is_shared
    assert services.generate_share_token(artifact) == token

    services.clear_share_token(artifact)
    assert artifact.share_token is None
    assert artifact.visibility == Visibility.PRIVATE


# --- views --------------------------------------------------------------------


def test_list_requires_login(client):
    response = client.get(reverse("artifacts:list"))

    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_detail_requires_login(client):
    user = make_user()
    artifact = services.create_artifact(user, title="Report", content="# A")

    response = client.get(reverse("artifacts:detail", args=[artifact.slug]))

    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_list_shows_only_own_artifacts(client):
    user = make_user("reader")
    other = make_user("other")
    services.create_artifact(user, title="Mine", content="# Mine")
    services.create_artifact(other, title="Theirs", content="# Theirs")
    client.force_login(user)

    content = client.get(reverse("artifacts:list")).content

    assert b"Mine" in content
    assert b"Theirs" not in content


def test_detail_is_owner_scoped(client):
    owner = make_user("owner")
    other = make_user("other")
    artifact = services.create_artifact(owner, title="Report", content="# A")
    client.force_login(other)

    response = client.get(reverse("artifacts:detail", args=[artifact.slug]))

    assert response.status_code == 404


def test_shared_page_renders_unlisted_artifact(client):
    user = make_user()
    artifact = services.create_artifact(user, title="Report", content="# Shared body")
    token = services.generate_share_token(artifact)

    response = client.get(reverse("artifacts:shared", args=[token]))

    assert response.status_code == 200
    assert b"Shared body" in response.content


def test_private_artifact_share_token_is_not_public(client):
    user = make_user()
    artifact = services.create_artifact(user, title="Report", content="# A")
    artifact.share_token = "leaked-token"
    artifact.save(update_fields=["share_token"])

    response = client.get(reverse("artifacts:shared", args=["leaked-token"]))

    assert response.status_code == 404


def test_clearing_share_token_disables_the_link(client):
    user = make_user()
    artifact = services.create_artifact(user, title="Report", content="# A")
    token = services.generate_share_token(artifact)
    services.clear_share_token(artifact)

    assert client.get(reverse("artifacts:shared", args=[token])).status_code == 404


def test_detail_shows_share_url_when_shared(client):
    user = make_user()
    artifact = services.create_artifact(user, title="Report", content="# A")
    token = services.generate_share_token(artifact)
    client.force_login(user)

    content = client.get(reverse("artifacts:detail", args=[artifact.slug])).content

    assert token.encode() in content
    assert b"data-copy-share" in content


def test_detail_includes_mermaid_scripts(client):
    user = make_user()
    artifact = services.create_artifact(
        user, title="Diagram", content="```mermaid\ngraph TD; A-->B;\n```"
    )
    client.force_login(user)

    content = client.get(reverse("artifacts:detail", args=[artifact.slug])).content

    assert b"mermaid-render.js" in content


def test_nav_links_to_artifacts(client):
    assert b"/artifacts/" in client.get(reverse("home")).content
