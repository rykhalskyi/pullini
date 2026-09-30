"""Wiki generation, markup and read-only view tests."""

from __future__ import annotations

import pytest
from django.urls import reverse

from pullini.projects.models import Project
from pullini.projects.sync import sync_project
from pullini.wiki import markup
from pullini.wiki.generation import generate_pages

pytestmark = pytest.mark.django_db


# --- markup -----------------------------------------------------------------


def test_render_supports_common_markup():
    html = markup.render("# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```\ncode\n```\n")

    assert "<h1" in html
    assert "<table>" in html
    assert "<code>" in html


def test_plain_text_strips_tags():
    assert markup.to_plain_text("<h1>Hi</h1>\n<p>There</p>") == "Hi There"


def test_extract_title_prefers_first_h1():
    assert markup.extract_title("intro\n# Real Title\n", "fallback") == "Real Title"
    assert markup.extract_title("no heading here", "fallback") == "fallback"


@pytest.mark.parametrize(
    ("path", "expected"),
    [("a/b.md", "a/b"), ("a/b.markdown", "a/b"), ("README.md", "README")],
)
def test_url_path_for(path, expected):
    assert markup.url_path_for(path) == expected


def test_rewrite_relative_markdown_link():
    html = markup.rewrite_urls('<a href="other.md#x">link</a>', "payments", "guide")

    assert 'href="/projects/payments/wiki/guide/other/#x"' in html


def test_rewrite_relative_image():
    html = markup.rewrite_urls('<img src="img/a.png">', "payments", "guide")

    assert 'src="/projects/payments/wiki/assets/guide/img/a.png"' in html


def test_rewrite_leaves_external_links_untouched():
    html = '<a href="https://example.com">x</a>'

    assert markup.rewrite_urls(html, "payments", "guide") == html


# --- generation -------------------------------------------------------------


def test_sync_generates_pages(project, remote_repo):
    remote_repo.write("docs/guide/setup.md", "# Setup\n\nInstall it.\n")

    sync_project(project, force=True)

    assert set(project.pages.values_list("path", flat=True)) == {
        "index.md",
        "guide/setup.md",
    }
    setup = project.pages.get(path="guide/setup.md")
    assert setup.title == "Setup"
    assert "Install it." in setup.html
    assert setup.plain_text == "Setup Install it."


def test_generation_is_idempotent(project):
    sync_project(project, force=True)
    page = project.pages.get(path="index.md")
    first_updated = page.updated_at

    changed = generate_pages(project)

    page.refresh_from_db()
    assert changed == 0
    assert page.updated_at == first_updated


def test_regeneration_removes_deleted_pages(project, remote_repo):
    remote_repo.write("docs/extra.md", "# Extra\n")
    sync_project(project, force=True)
    assert project.pages.filter(path="extra.md").exists()

    remote_repo.remove("docs/extra.md")
    sync_project(project, force=True)

    assert not project.pages.filter(path="extra.md").exists()


# --- views ------------------------------------------------------------------


def test_wiki_tree_lists_pages(client, project, remote_repo):
    remote_repo.write("docs/guide/setup.md", "# Setup\n")
    sync_project(project, force=True)

    response = client.get(reverse("wiki:tree", args=[project.slug]))

    assert response.status_code == 200
    assert b"Setup" in response.content


def test_wiki_index_and_recent(client, project):
    sync_project(project, force=True)

    assert b"Home" in client.get(reverse("wiki:index", args=[project.slug])).content
    assert b"Home" in client.get(reverse("wiki:recent", args=[project.slug])).content


def test_wiki_page_renders_content_and_source_path(client, project):
    sync_project(project, force=True)
    page = project.pages.get(path="index.md")

    response = client.get(reverse("wiki:page", args=[project.slug, page.url_path]))

    assert response.status_code == 200
    assert b"Home" in response.content
    assert page.path.encode() in response.content


def test_wiki_page_unknown_is_404(client, project):
    sync_project(project, force=True)

    assert client.get(reverse("wiki:page", args=[project.slug, "nope"])).status_code == 404


def test_wiki_asset_is_served(client, project, remote_repo):
    remote_repo.write("docs/img/logo.svg", "<svg></svg>")
    sync_project(project, force=True)

    response = client.get(reverse("wiki:asset", args=[project.slug, "img/logo.svg"]))

    assert response.status_code == 200
    assert b"<svg>" in b"".join(response.streaming_content)


def test_wiki_asset_missing_is_404(client, project):
    sync_project(project, force=True)

    assert client.get(reverse("wiki:asset", args=[project.slug, "nope.png"])).status_code == 404


def test_wiki_hidden_for_disabled_project(client, remote_repo):
    hidden = Project.objects.create(
        name="Hidden",
        repo_url=f"file://{remote_repo.bare}",
        enabled=False,
    )

    assert client.get(reverse("wiki:tree", args=[hidden.slug])).status_code == 404
