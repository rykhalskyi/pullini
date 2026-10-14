"""Tests for the MCP tool surface (E6, T6).

The tools only translate arguments into :class:`PulliniClient` calls, so these
tests exercise them against a recording fake rather than a live host.
"""

from __future__ import annotations

import pytest

from pullini_mcp import server
from pullini_mcp.client import PulliniError


class FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.artifact: dict = {"slug": "notes", "title": "Notes", "share_url": None}

    def create_artifact(self, title, content, visibility="private", tags=None):
        self.calls.append(("create", title, content, visibility, tags))
        self.artifact = {"slug": "notes", "title": title, "share_url": None, "tags": tags or []}
        return self.artifact

    def list_artifacts(self):
        self.calls.append(("list",))
        return [self.artifact]

    def get_artifact(self, slug):
        self.calls.append(("get", slug))
        return self.artifact

    def update_artifact(self, slug, *, title=None, content=None, tags=None):
        self.calls.append(("update", slug, title, content, tags))
        self.artifact = {
            **self.artifact,
            "slug": slug,
            "title": title or self.artifact["title"],
            "tags": tags if tags is not None else self.artifact.get("tags", []),
        }
        return self.artifact

    def delete_artifact(self, slug):
        self.calls.append(("delete", slug))

    def list_tags(self):
        self.calls.append(("list_tags",))
        return [{"name": "Notes", "slug": "notes", "count": 1}]

    def delete_tag(self, slug):
        self.calls.append(("delete_tag", slug))

    def share_artifact(self, slug, *, enable=True):
        self.calls.append(("share", slug, enable))
        self.artifact = {
            **self.artifact,
            "share_url": "https://pullini.test/a/t/" if enable else None,
        }
        return self.artifact if enable else None

    def list_pages(self, project=None):
        self.calls.append(("list_pages", project))
        return [{"project": "payments", "path": "index.md"}]

    def get_page(self, project, path):
        self.calls.append(("get_page", project, path))
        return {"project": project, "path": path, "content": "# Page"}

    def create_quiz(self, *, questions, page=None, artifact=None):
        self.calls.append(("create_quiz", questions, page, artifact))
        return {"id": 1, "questions": questions}

    def get_quiz(self, quiz_id):
        self.calls.append(("get_quiz", quiz_id))
        return {"id": quiz_id, "questions": []}

    def list_quizzes(self):
        self.calls.append(("list_quizzes",))
        return [{"id": 1}]

    def delete_quiz(self, quiz_id):
        self.calls.append(("delete_quiz", quiz_id))

    def create_qanda(self, *, entries, page=None, artifact=None):
        self.calls.append(("create_qanda", entries, page, artifact))
        return {"id": 1, "items": entries}

    def get_qanda(self, qanda_id):
        self.calls.append(("get_qanda", qanda_id))
        return {"id": qanda_id, "items": []}

    def list_qanda(self):
        self.calls.append(("list_qanda",))
        return [{"id": 1}]

    def delete_qanda(self, qanda_id):
        self.calls.append(("delete_qanda", qanda_id))

    def close(self):
        self.calls.append(("close",))


@pytest.fixture()
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(server, "_client", lambda: client)
    return client


def test_tool_names_are_registered():
    tools = {tool.name for tool in _list_tools()}

    assert tools == {
        "store_artifact",
        "list_artifacts",
        "get_artifact",
        "update_artifact",
        "delete_artifact",
        "share_artifact",
        "list_tags",
        "delete_tag",
        "list_pages",
        "get_page",
        "create_quiz",
        "get_quiz",
        "list_quizzes",
        "delete_quiz",
        "create_qanda",
        "get_qanda",
        "list_qanda",
        "delete_qanda",
    }


def _list_tools():
    import asyncio

    return asyncio.run(server.mcp.list_tools())


def test_store_creates_when_no_slug(fake):
    result = server.store_artifact("Notes", "# Notes", "unlisted")

    assert result["slug"] == "notes"
    assert fake.calls[0] == ("create", "Notes", "# Notes", "unlisted", None)
    assert fake.calls[-1] == ("close",)


def test_store_passes_tags_on_create_and_overwrite(fake):
    server.store_artifact("Notes", "# Notes", tags=["work"])
    server.store_artifact("Notes", "# Notes", slug="notes", tags=["home"])

    assert ("create", "Notes", "# Notes", "private", ["work"]) in fake.calls
    assert ("update", "notes", "Notes", "# Notes", ["home"]) in fake.calls


def test_store_rejects_bad_visibility(fake):
    with pytest.raises(PulliniError, match="visibility"):
        server.store_artifact("Notes", "# Notes", "public")

    assert fake.calls == []


def test_store_overwrites_and_shares_when_slug_given(fake):
    server.store_artifact("Notes", "# Notes", "unlisted", slug="notes")

    assert ("update", "notes", "Notes", "# Notes", None) in fake.calls
    assert ("share", "notes", True) in fake.calls


def test_store_overwrite_private_revokes_share(fake):
    fake.artifact["share_url"] = "https://pullini.test/a/t/"

    result = server.store_artifact("Notes", "# Notes", "private", slug="notes")

    assert ("share", "notes", False) in fake.calls
    assert result["share_url"] is None


def test_list_get_update_delete_share_delegate(fake):
    assert server.list_artifacts() == [fake.artifact]
    server.get_artifact("notes")
    server.update_artifact("notes", content="# New")
    server.delete_artifact("notes")
    server.share_artifact("notes")

    assert ("get", "notes") in fake.calls
    assert ("update", "notes", None, "# New", None) in fake.calls
    assert ("delete", "notes") in fake.calls
    assert ("share", "notes", True) in fake.calls


def test_update_passes_tags(fake):
    server.update_artifact("notes", tags=["work", "urgent"])

    assert ("update", "notes", None, None, ["work", "urgent"]) in fake.calls


def test_delete_reports_confirmation(fake):
    assert server.delete_artifact("notes") == {"slug": "notes", "deleted": True}


def test_list_tags_delegates(fake):
    assert server.list_tags() == [{"name": "Notes", "slug": "notes", "count": 1}]
    assert ("list_tags",) in fake.calls


def test_delete_tag_reports_confirmation(fake):
    assert server.delete_tag("notes") == {"slug": "notes", "deleted": True}
    assert ("delete_tag", "notes") in fake.calls


def test_revoke_share_returns_cleared_link(fake):
    assert server.share_artifact("notes", enable=False) == {"slug": "notes", "share_url": None}


def test_page_tools_delegate(fake):
    assert server.list_pages("payments") == [{"project": "payments", "path": "index.md"}]
    server.get_page("payments", "index.md")

    assert ("list_pages", "payments") in fake.calls
    assert ("get_page", "payments", "index.md") in fake.calls


def test_create_quiz_delegates(fake):
    questions = [{"text": "Q", "options": ["a", "b"], "correct_index": 0}]

    server.create_quiz(questions, page={"project": "payments", "path": "index.md"})

    assert (
        "create_quiz",
        questions,
        {"project": "payments", "path": "index.md"},
        None,
    ) in fake.calls


def test_create_quiz_requires_exactly_one_target(fake):
    with pytest.raises(PulliniError, match="exactly one"):
        server.create_quiz([], page={"project": "p", "path": "x.md"}, artifact="a")
    with pytest.raises(PulliniError, match="exactly one"):
        server.create_quiz([])

    assert fake.calls == []


def test_quiz_read_and_delete_delegate(fake):
    server.get_quiz(1)
    assert server.list_quizzes() == [{"id": 1}]
    assert server.delete_quiz(1) == {"id": 1, "deleted": True}

    assert ("get_quiz", 1) in fake.calls
    assert ("list_quizzes",) in fake.calls
    assert ("delete_quiz", 1) in fake.calls


def test_create_qanda_delegates(fake):
    entries = [{"question": "Q", "answer": "A"}]

    server.create_qanda(entries, page={"project": "payments", "path": "index.md"})

    assert (
        "create_qanda",
        entries,
        {"project": "payments", "path": "index.md"},
        None,
    ) in fake.calls


def test_create_qanda_requires_exactly_one_target(fake):
    with pytest.raises(PulliniError, match="exactly one"):
        server.create_qanda([], page={"project": "p", "path": "x.md"}, artifact="a")
    with pytest.raises(PulliniError, match="exactly one"):
        server.create_qanda([])

    assert fake.calls == []


def test_qanda_read_and_delete_delegate(fake):
    server.get_qanda(1)
    assert server.list_qanda() == [{"id": 1}]
    assert server.delete_qanda(1) == {"id": 1, "deleted": True}

    assert ("get_qanda", 1) in fake.calls
    assert ("list_qanda",) in fake.calls
    assert ("delete_qanda", 1) in fake.calls


def test_skill_resource_is_registered():
    resources = {str(resource.uri) for resource in _list_resources()}

    assert "pullini://skill" in resources


def test_skill_resource_returns_the_tool_guide():
    contents = _read_resource("pullini://skill")

    assert contents[0].mime_type == "text/markdown"
    assert "store_artifact" in contents[0].content


def _list_resources():
    import asyncio

    return asyncio.run(server.mcp.list_resources())


def _read_resource(uri):
    import asyncio

    return list(asyncio.run(server.mcp.read_resource(uri)))
