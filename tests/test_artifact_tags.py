"""Artifact tag tests: services and the web controls (E6, T8/D-37/D-38)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from pullini.artifacts import services
from pullini.artifacts.models import Tag

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def make_artifact(user, title: str = "Report", tags=None):
    return services.create_artifact(user, title=title, content="# A", tags=tags)


# --- services -----------------------------------------------------------------


def test_resolve_tags_creates_tags_lazily():
    user = make_user()

    tags = services.resolve_tags(user, ["Work"])

    assert [tag.name for tag in tags] == ["Work"]
    assert tags[0].slug == "work"
    assert Tag.objects.filter(user=user).count() == 1


def test_existing_tag_is_reused_and_keeps_the_first_display_case():
    user = make_user()

    first = services.resolve_tags(user, ["Weekly Report"])[0]
    again = services.resolve_tags(user, ["  weekly   report "])[0]

    assert first.pk == again.pk
    assert again.name == "Weekly Report"
    assert Tag.objects.filter(user=user).count() == 1


def test_names_are_normalized():
    user = make_user()

    tag = services.resolve_tags(user, ["  Hello   World  "])[0]

    assert tag.name == "Hello World"
    assert tag.slug == "hello-world"


def test_resolve_tags_dedupes_case_insensitively():
    user = make_user()

    assert len(services.resolve_tags(user, ["Work", "work", "WORK"])) == 1


def test_non_latin_names_get_unicode_slugs():
    user = make_user()

    tags = services.resolve_tags(user, ["Привіт", "Café"])

    assert {tag.slug for tag in tags} == {"привіт", "café"}
    assert {tag.name for tag in tags} == {"Привіт", "Café"}


@pytest.mark.parametrize("bad", ["", "   ", "!!!", "x" * (services.MAX_TAG_NAME + 1)])
def test_invalid_names_raise(bad):
    user = make_user()

    with pytest.raises(services.TagError):
        services.resolve_tags(user, [bad])


def test_more_than_twenty_tags_raise_before_creating_any():
    user = make_user()

    with pytest.raises(services.TagError):
        services.resolve_tags(user, [f"tag-{i}" for i in range(21)])

    assert Tag.objects.filter(user=user).count() == 0


def test_tags_are_scoped_per_user():
    owner = make_user("owner")
    other = make_user("other")

    owner_tag = services.resolve_tags(owner, ["Shared"])[0]
    other_tag = services.resolve_tags(other, ["Shared"])[0]

    assert owner_tag.pk != other_tag.pk
    assert owner_tag.user == owner
    assert other_tag.user == other


def test_set_add_and_remove_tags():
    user = make_user()
    artifact = make_artifact(user)

    services.set_artifact_tags(artifact, ["A", "B"])
    assert set(artifact.tags.values_list("name", flat=True)) == {"A", "B"}

    services.set_artifact_tags(artifact, ["C"])
    assert set(artifact.tags.values_list("name", flat=True)) == {"C"}

    services.add_tags(artifact, ["D"])
    assert set(artifact.tags.values_list("name", flat=True)) == {"C", "D"}

    services.remove_tags(artifact, ["c"])
    assert set(artifact.tags.values_list("name", flat=True)) == {"D"}


def test_create_artifact_accepts_tags():
    user = make_user()

    artifact = services.create_artifact(user, title="Report", content="# A", tags=["x", "y"])

    assert set(artifact.tags.values_list("slug", flat=True)) == {"x", "y"}


def test_add_tags_respects_the_artifact_cap():
    user = make_user()
    artifact = make_artifact(user)
    services.set_artifact_tags(artifact, [f"t{i}" for i in range(services.MAX_TAGS_PER_ARTIFACT)])

    with pytest.raises(services.TagError):
        services.add_tags(artifact, ["one-too-many"])

    assert artifact.tags.count() == services.MAX_TAGS_PER_ARTIFACT


def test_delete_tag_removes_it_everywhere_but_keeps_orphans():
    user = make_user()
    artifact = make_artifact(user, tags=["Work"])
    services.resolve_tags(user, ["Unused"])

    assert services.delete_tag(user, "work") is True
    assert not Tag.objects.filter(user=user, slug="work").exists()
    assert artifact.tags.count() == 0
    assert Tag.objects.filter(user=user, slug="unused").exists()
    assert services.delete_tag(user, "work") is False


def test_tags_with_counts_includes_empty_tags():
    user = make_user()
    make_artifact(user, title="A", tags=["one", "two"])
    make_artifact(user, title="B", tags=["two"])
    services.resolve_tags(user, ["unused"])

    counts = {tag.slug: tag.count for tag in services.tags_with_counts(user)}

    assert counts == {"one": 1, "two": 2, "unused": 0}


# --- web ----------------------------------------------------------------------


def test_tag_controls_require_login(client):
    user = make_user()
    artifact = make_artifact(user)

    for url in (
        reverse("artifacts:tag_add", args=[artifact.slug]),
        reverse("artifacts:tag_remove", args=[artifact.slug, "work"]),
        reverse("artifacts:tag_delete", args=["work"]),
    ):
        response = client.post(url)
        assert response.status_code == 302
        assert response.url.startswith("/login/")


def test_tag_add_creates_and_redirects(client):
    user = make_user("owner")
    artifact = make_artifact(user)
    client.force_login(user)

    response = client.post(reverse("artifacts:tag_add", args=[artifact.slug]), {"name": "Work"})

    assert response.status_code == 302
    assert artifact.tags.filter(slug="work").exists()


def test_tag_add_returns_an_htmx_partial(client):
    user = make_user("owner")
    artifact = make_artifact(user)
    client.force_login(user)

    response = client.post(
        reverse("artifacts:tag_add", args=[artifact.slug]),
        {"name": "Work"},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert b"Work" in response.content
    assert b"artifact-tags-" in response.content


def test_tag_add_is_owner_scoped(client):
    owner = make_user("owner")
    other = make_user("other")
    artifact = make_artifact(owner)
    client.force_login(other)

    response = client.post(reverse("artifacts:tag_add", args=[artifact.slug]), {"name": "Work"})

    assert response.status_code == 404


def test_tag_remove_detaches_but_keeps_the_vocabulary(client):
    user = make_user("owner")
    artifact = make_artifact(user, tags=["Work"])
    client.force_login(user)

    response = client.post(reverse("artifacts:tag_remove", args=[artifact.slug, "work"]))

    assert response.status_code == 302
    assert artifact.tags.count() == 0
    assert Tag.objects.filter(user=user, slug="work").exists()


def test_tag_remove_is_owner_scoped(client):
    owner = make_user("owner")
    other = make_user("other")
    artifact = make_artifact(owner, tags=["Work"])
    client.force_login(other)

    response = client.post(reverse("artifacts:tag_remove", args=[artifact.slug, "work"]))

    assert response.status_code == 404


def test_tag_delete_removes_it_and_redirects(client):
    user = make_user("owner")
    artifact = make_artifact(user, tags=["Work"])
    client.force_login(user)

    response = client.post(reverse("artifacts:tag_delete", args=["work"]))

    assert response.status_code == 302
    assert not Tag.objects.filter(user=user).exists()
    assert artifact.tags.count() == 0


def test_tag_delete_is_owner_scoped(client):
    owner = make_user("owner")
    other = make_user("other")
    services.resolve_tags(owner, ["Work"])
    client.force_login(other)

    response = client.post(reverse("artifacts:tag_delete", args=["work"]))

    assert response.status_code == 404


def test_unicode_tag_web_round_trip(client):
    user = make_user("owner")
    artifact = make_artifact(user)
    client.force_login(user)
    slug = "привіт"

    added = client.post(reverse("artifacts:tag_add", args=[artifact.slug]), {"name": "Привіт"})
    assert added.status_code == 302
    assert artifact.tags.filter(slug=slug).exists()

    removed = client.post(reverse("artifacts:tag_remove", args=[artifact.slug, slug]))
    assert removed.status_code == 302
    assert artifact.tags.count() == 0
    assert Tag.objects.filter(user=user, slug=slug).exists()

    deleted = client.post(reverse("artifacts:tag_delete", args=[slug]))
    assert deleted.status_code == 302
    assert not Tag.objects.filter(user=user, slug=slug).exists()


def test_tag_add_reports_a_validation_error(client):
    user = make_user("owner")
    artifact = make_artifact(user)
    client.force_login(user)

    response = client.post(
        reverse("artifacts:tag_add", args=[artifact.slug]),
        {"name": "x" * (services.MAX_TAG_NAME + 1)},
        follow=True,
    )

    assert response.status_code == 200
    assert b"at most 50 characters" in response.content
    assert artifact.tags.count() == 0


def test_tag_add_reports_the_error_in_the_htmx_partial(client):
    user = make_user("owner")
    artifact = make_artifact(user)
    client.force_login(user)

    response = client.post(
        reverse("artifacts:tag_add", args=[artifact.slug]),
        {"name": "x" * (services.MAX_TAG_NAME + 1)},
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200
    assert b"at most 50 characters" in response.content
    assert artifact.tags.count() == 0


def test_tag_endpoints_reject_get(client):
    user = make_user("owner")
    artifact = make_artifact(user)
    client.force_login(user)

    assert client.get(reverse("artifacts:tag_add", args=[artifact.slug])).status_code == 405
    assert client.get(reverse("artifacts:tag_delete", args=["work"])).status_code == 405


def test_list_filters_by_tag(client):
    user = make_user("owner")
    make_artifact(user, title="Tagged", tags=["Work"])
    make_artifact(user, title="Untagged")
    client.force_login(user)

    content = client.get(reverse("artifacts:list"), {"tag": "work"}).content

    assert b"Tagged" in content
    assert b"Untagged" not in content


def test_list_ignores_an_unknown_tag_filter(client):
    user = make_user("owner")
    make_artifact(user, title="Tagged", tags=["Work"])
    client.force_login(user)

    content = client.get(reverse("artifacts:list"), {"tag": "nope"}).content

    assert b"Tagged" in content


def test_detail_shows_editable_tags(client):
    user = make_user("owner")
    artifact = make_artifact(user, tags=["Work"])
    client.force_login(user)

    content = client.get(reverse("artifacts:detail", args=[artifact.slug])).content

    assert b"Work" in content
    assert b"Add tag" in content


def test_shared_page_shows_tags_read_only(client):
    user = make_user()
    artifact = make_artifact(user, tags=["Work"])
    token = services.generate_share_token(artifact)

    response = client.get(reverse("artifacts:shared", args=[token]))

    assert response.status_code == 200
    assert b"Work" in response.content
    assert b"Add tag" not in response.content
