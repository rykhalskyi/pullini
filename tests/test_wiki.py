"""Wiki generation, markup and read-only view tests."""

from __future__ import annotations

import shutil

import pytest
from django.urls import reverse

from pullini.projects.models import Project
from pullini.projects.sync import repository_path, sync_project
from pullini.wiki import markup
from pullini.wiki.generation import generate_pages

pytestmark = pytest.mark.django_db


# --- markup -----------------------------------------------------------------


def test_render_supports_common_markup():
    html = markup.render("# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n```\ncode\n```\n")

    assert "<h1" in html
    assert "<table>" in html
    assert "<code>" in html


def test_render_strips_scripts_and_event_handlers():
    html = markup.render(
        "<script>alert(1)</script>\n\n<img src=x onerror=alert(2)>\n\n<iframe src=y></iframe>"
    )

    assert "<script" not in html
    assert "onerror" not in html
    assert "<iframe" not in html


@pytest.mark.parametrize(
    "content",
    [
        '<a href="javascript:alert(1)">x</a>',
        "<a href='javascript:alert(1)'>x</a>",
        '<a href="data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==">x</a>',
    ],
)
def test_render_strips_dangerous_url_schemes(content):
    html = markup.render(content)

    assert "javascript:" not in html
    assert "data:" not in html
    assert "href" not in html


def test_render_keeps_safe_markup():
    content = (
        "# Title\n\n"
        "[link](https://example.com)\n\n"
        "```python\nprint(1)\n```\n\n"
        "| A | B |\n|---|---|\n| 1 | 2 |\n"
    )
    html = markup.render(content)

    assert '<h1 id="title">' in html or "<h1" in html
    assert 'href="https://example.com"' in html
    assert 'class="language-python"' in html
    assert "<table>" in html


def test_render_converts_mermaid_fences_to_containers():
    html = markup.render("```mermaid\ngraph TD\n  A-->B\n```\n")

    assert '<div class="mermaid">' in html
    assert "graph TD" in html
    assert "language-mermaid" not in html


def test_render_keeps_non_mermaid_fences_as_code():
    html = markup.render("```python\nprint(1)\n```\n")

    assert '<pre><code class="language-python">' in html
    assert '<div class="mermaid">' not in html


def test_render_mermaid_source_is_inert():
    html = markup.render("```mermaid\ngraph TD\n  A[<script>alert(1)</script>]\n```\n")

    assert "<script" not in html
    assert '<div class="mermaid">' in html


def test_render_mermaid_drops_config_directives():
    html = markup.render(
        '```mermaid\n%%{init: {"securityLevel": "loose"}}%%\ngraph TD\n  A-->B\n```\n'
    )

    assert "%%{" not in html
    assert "securityLevel" not in html
    assert "graph TD" in html


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


def test_generation_ignores_symlinked_files(project, remote_repo, tmp_path):
    secret = tmp_path / "secret.md"
    secret.write_text("# Secret\n\nTOPSECRET\n")
    sync_project(project, force=True)

    (repository_path(project) / "docs" / "leak.md").symlink_to(secret)

    generate_pages(project)

    assert not project.pages.filter(path="leak.md").exists()


def test_generation_ignores_symlinked_docs_folder(project, remote_repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.md").write_text("# X\n")
    sync_project(project, force=True)

    repo_docs = repository_path(project) / "docs"
    shutil.rmtree(repo_docs)
    repo_docs.symlink_to(outside, target_is_directory=True)

    generate_pages(project)

    assert not project.pages.filter(path="x.md").exists()


# --- views ------------------------------------------------------------------


def test_wiki_tree_lists_pages(client, project, remote_repo):
    remote_repo.write("docs/guide/setup.md", "# Setup\n")
    sync_project(project, force=True)

    response = client.get(reverse("wiki:tree", args=[project.slug]))

    assert response.status_code == 200
    assert b"Setup" in response.content


def test_wiki_recent(client, project):
    sync_project(project, force=True)

    assert b"Home" in client.get(reverse("wiki:recent", args=[project.slug])).content


def test_wiki_page_renders_content_and_source_path(client, project):
    sync_project(project, force=True)
    page = project.pages.get(path="index.md")

    response = client.get(reverse("wiki:page", args=[project.slug, page.url_path]))

    assert response.status_code == 200
    assert b"Home" in response.content
    assert page.path.encode() in response.content


def test_wiki_page_renders_code_blocks_with_copy_script(client, project, remote_repo):
    remote_repo.write("docs/code.md", "# Code\n\n```python\nprint('hi')\n```\n")
    sync_project(project, force=True)
    page = project.pages.get(path="code.md")

    response = client.get(reverse("wiki:page", args=[project.slug, page.url_path]))

    assert b"<pre>" in response.content
    assert b"js/copy-code.js" in response.content
    assert b"js/mermaid-render.js" not in response.content


def test_wiki_page_loads_mermaid_only_for_diagram_pages(client, project, remote_repo):
    remote_repo.write("docs/diagram.md", "# Diagram\n\n```mermaid\ngraph TD\n  A-->B\n```\n")
    sync_project(project, force=True)
    page = project.pages.get(path="diagram.md")

    response = client.get(reverse("wiki:page", args=[project.slug, page.url_path]))

    assert response.status_code == 200
    assert b'class="mermaid"' in response.content
    assert b"js/vendor/mermaid.min.js" in response.content
    assert b"js/mermaid-render.js" in response.content


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


def test_wiki_asset_scriptable_types_are_downloaded(client, project, remote_repo):
    remote_repo.write("docs/img/logo.svg", "<svg onload=alert(1)></svg>")
    sync_project(project, force=True)

    response = client.get(reverse("wiki:asset", args=[project.slug, "img/logo.svg"]))

    assert response.status_code == 200
    assert response["Content-Disposition"].startswith("attachment")
    assert response["X-Content-Type-Options"] == "nosniff"


def test_wiki_asset_images_are_inline(client, project, remote_repo):
    remote_repo.write("docs/img/logo.png", "not-a-real-png")
    sync_project(project, force=True)

    response = client.get(reverse("wiki:asset", args=[project.slug, "img/logo.png"]))

    assert response.status_code == 200
    assert not response["Content-Disposition"].startswith("attachment")
    assert response["X-Content-Type-Options"] == "nosniff"


def test_wiki_hidden_for_disabled_project(client, remote_repo):
    hidden = Project.objects.create(
        name="Hidden",
        repo_url=f"file://{remote_repo.bare}",
        enabled=False,
    )

    assert client.get(reverse("wiki:tree", args=[hidden.slug])).status_code == 404
