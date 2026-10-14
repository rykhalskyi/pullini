"""Q&A tests: models, services and the web surface (E6, T12/D-43…D-45)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse

from pullini.artifacts import services as artifact_services
from pullini.projects.models import Project
from pullini.qanda import services
from pullini.qanda.models import QandA
from pullini.wiki.models import Page

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def make_project(name: str = "Payments", *, enabled: bool = True) -> Project:
    return Project.objects.create(
        name=name,
        repo_url="https://git.example.com/payments.git",
        enabled=enabled,
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


def e(question: str = "Q", answer: str = "A"):
    return {"question": question, "answer": answer}


# --- models & creation --------------------------------------------------------


def test_create_qanda_creates_ordered_items():
    user = make_user()
    page = make_page(make_project())

    qanda = services.create_qanda(user, page=page, entries=[e("First"), e("Second", "B")])

    assert qanda.user == user
    assert qanda.target_type == "page"
    assert qanda.source_hash == page.content_hash
    assert [item.question for item in qanda.items.all()] == ["First", "Second"]
    assert [item.position for item in qanda.items.all()] == [0, 1]
    assert qanda.item_count == 2


def test_qanda_is_unique_per_user_and_page():
    user = make_user()
    page = make_page(make_project())
    services.create_qanda(user, page=page, entries=[e()])

    with pytest.raises(IntegrityError), transaction.atomic():
        QandA.objects.create(user=user, page=page, target_type="page", source_hash="x")


def test_qanda_requires_exactly_one_target():
    user = make_user()
    page = make_page(make_project())
    artifact = make_artifact(user)

    with pytest.raises(IntegrityError), transaction.atomic():
        QandA.objects.create(
            user=user, page=page, artifact=artifact, target_type="page", source_hash="x"
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        QandA.objects.create(user=user, target_type="page", source_hash="x")


def test_create_qanda_replaces_the_existing_one():
    user = make_user()
    page = make_page(make_project())
    first = services.create_qanda(user, page=page, entries=[e("Old"), e("Also old")])

    second = services.create_qanda(user, page=page, entries=[e("New")])

    assert second.pk == first.pk
    assert QandA.objects.filter(user=user, page=page).count() == 1
    assert [item.question for item in second.items.all()] == ["New"]


def test_create_qanda_for_an_artifact():
    user = make_user()
    artifact = make_artifact(user)

    qanda = services.create_qanda(user, artifact=artifact, entries=[e()])

    assert qanda.target_type == "artifact"
    assert qanda.target == artifact
    assert qanda.source_hash == artifact.content_hash


def test_qanda_are_scoped_per_user():
    page = make_page(make_project())
    owner = make_user("owner")
    other = make_user("other")

    services.create_qanda(owner, page=page, entries=[e()])
    services.create_qanda(other, page=page, entries=[e("Other")])

    assert QandA.objects.filter(page=page).count() == 2
    assert services.get_qanda(owner, page=page).items.count() == 1


def test_cascade_deletes_qanda_with_its_source():
    user = make_user()
    page = make_page(make_project())
    artifact = make_artifact(user)
    services.create_qanda(user, page=page, entries=[e()])
    services.create_qanda(user, artifact=artifact, entries=[e()])

    page.delete()
    artifact.delete()

    assert QandA.objects.count() == 0


def test_is_stale_tracks_the_source_hash():
    user = make_user()
    page = make_page(make_project())
    services.create_qanda(user, page=page, entries=[e()])
    assert services.get_qanda(user, page=page).is_stale is False

    page.content_hash = "changed"
    page.save(update_fields=["content_hash"])

    assert services.get_qanda(user, page=page).is_stale is True


# --- validation ---------------------------------------------------------------


def test_create_qanda_requires_exactly_one_target():
    user = make_user()
    page = make_page(make_project())
    artifact = make_artifact(user)

    with pytest.raises(services.QandAError):
        services.create_qanda(user, entries=[e()])
    with pytest.raises(services.QandAError):
        services.create_qanda(user, page=page, artifact=artifact, entries=[e()])


@pytest.mark.parametrize(
    "entries",
    [
        [],
        [e()] * (services.MAX_ENTRIES + 1),
        [{"question": "", "answer": "A"}],
        [{"question": "Q", "answer": "  "}],
        [{"answer": "A"}],
        [{"question": "Q"}],
        "not-a-list",
    ],
)
def test_invalid_entries_are_rejected(entries):
    user = make_user()
    page = make_page(make_project())

    with pytest.raises(services.QandAError):
        services.create_qanda(user, page=page, entries=entries)

    assert QandA.objects.count() == 0


def test_answer_over_the_cap_is_rejected():
    user = make_user()
    page = make_page(make_project())

    with pytest.raises(services.QandAError):
        services.create_qanda(
            user, page=page, entries=[e(answer="x" * (services.MAX_ANSWER_TEXT + 1))]
        )


# --- markdown -----------------------------------------------------------------


def test_answer_html_is_rendered_markdown():
    user = make_user()
    page = make_page(make_project())

    qanda = services.create_qanda(
        user, page=page, entries=[e(answer="Use `pip install` and **read** more.")]
    )

    html = qanda.items.get().answer_html
    assert "<code>pip install</code>" in html
    assert "<strong>read</strong>" in html


def test_answer_html_is_sanitized():
    user = make_user()
    page = make_page(make_project())

    qanda = services.create_qanda(
        user, page=page, entries=[e(answer='Hello <script>alert("x")</script>')]
    )

    html = qanda.items.get().answer_html
    assert "<script>" not in html
    assert "alert" not in html


def test_has_mermaid_detects_diagram_answers():
    user = make_user()
    page = make_page(make_project())

    qanda = services.create_qanda(
        user, page=page, entries=[e(answer="```mermaid\ngraph TD;\nA-->B;\n```")]
    )

    assert qanda.has_mermaid is True
    assert qanda.items.get().answer_html.count('class="mermaid"') == 1


# --- web ----------------------------------------------------------------------


def test_qanda_view_requires_login(client):
    user = make_user()
    qanda = services.create_qanda(user, page=make_page(make_project()), entries=[e()])

    response = client.get(reverse("qanda:detail", args=[qanda.pk]))

    assert response.status_code == 302
    assert response.url.startswith("/login/")


def test_qanda_is_owner_scoped(client):
    owner = make_user("owner")
    other = make_user("other")
    qanda = services.create_qanda(owner, page=make_page(make_project()), entries=[e()])
    client.force_login(other)

    assert client.get(reverse("qanda:detail", args=[qanda.pk])).status_code == 404


def test_qanda_detail_shows_questions_and_answers(client):
    user = make_user()
    client.force_login(user)
    qanda = services.create_qanda(
        user,
        page=make_page(make_project()),
        entries=[e("What is 2+2?", "It is **4**.")],
    )

    content = client.get(reverse("qanda:detail", args=[qanda.pk])).content

    assert b"What is 2+2?" in content
    assert b"<strong>4</strong>" in content
    assert b"Back to article" in content


def test_qanda_detail_flags_a_stale_set(client):
    user = make_user()
    client.force_login(user)
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    qanda = services.create_qanda(user, page=page, entries=[e()])
    page.content_hash = "changed"
    page.save(update_fields=["content_hash"])

    content = client.get(reverse("qanda:detail", args=[qanda.pk])).content

    assert b"out of date" in content


def test_wiki_page_shows_qanda_button(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    qanda = services.create_qanda(user, page=page, entries=[e(), e()])
    client.force_login(user)

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert reverse("qanda:detail", args=[qanda.pk]).encode() in content
    assert b"Q&amp;A" in content


def test_wiki_page_shows_no_qanda_hint(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    client.force_login(user)

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert b"No Q&amp;A yet" in content
    assert b"Create a Q&amp;A set" in content
    assert f"{project.slug}/{page.path}".encode() in content


def test_artifact_detail_no_qanda_hint_copies_slug(client):
    user = make_user()
    artifact = make_artifact(user)
    client.force_login(user)

    content = client.get(reverse("artifacts:detail", args=[artifact.slug])).content

    assert b"Create a Q&amp;A set" in content
    assert b"data-qanda-ref" in content
    assert b"data-copy-qanda-ref" in content


def test_artifact_detail_shows_qanda_button(client):
    user = make_user()
    artifact = make_artifact(user)
    qanda = services.create_qanda(user, artifact=artifact, entries=[e()])
    client.force_login(user)

    content = client.get(reverse("artifacts:detail", args=[artifact.slug])).content

    assert reverse("qanda:detail", args=[qanda.pk]).encode() in content


def test_project_detail_lists_page_qanda(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    services.create_qanda(user, page=page, entries=[e()])
    client.force_login(user)

    content = client.get(reverse("projects:detail", args=[project.slug])).content

    assert b"Q&amp;A" in content
    assert b"Home" in content


def test_anonymous_wiki_page_shows_no_qanda_affordance(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    services.create_qanda(user, page=page, entries=[e()])

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert b"No Q&amp;A yet" not in content
