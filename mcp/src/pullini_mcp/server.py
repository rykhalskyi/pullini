"""MCP stdio server exposing Pullini artifacts as MCP tools (E6, T6).

Every tool is a thin translation of an MCP call into a
:class:`~pullini_mcp.client.PulliniClient` request. Configuration comes from the
environment (``PULLINI_URL``/``PULLINI_TOKEN``, D-25), so the server holds no
state between calls and needs no ASGI/OAuth infrastructure on the Pullini host.

In ``mcp`` 2.x the server class formerly named ``FastMCP`` is ``MCPServer``.
"""

from __future__ import annotations

from importlib.resources import files

from mcp.server.mcpserver import MCPServer

from pullini_mcp import __version__
from pullini_mcp.client import Config, PulliniClient, PulliniError

mcp = MCPServer("pullini", version=__version__)

_VISIBILITIES = ("private", "unlisted")


def _client() -> PulliniClient:
    return PulliniClient(Config.from_env())


def _check_visibility(visibility: str) -> str:
    if visibility not in _VISIBILITIES:
        raise PulliniError('"visibility" must be "private" or "unlisted".')
    return visibility


@mcp.tool()
def store_artifact(
    title: str,
    content: str,
    visibility: str = "private",
    slug: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Create an artifact, or overwrite the artifact identified by ``slug``.

    Args:
        title: Short human-readable title.
        content: Markdown source; fenced ``mermaid`` blocks render as diagrams.
        visibility: ``"private"`` (default) or ``"unlisted"`` (active share link).
        slug: When given, overwrite that artifact instead of creating a new one.
        tags: Optional list of tag names; replace the artifact's tags when given.
    """
    _check_visibility(visibility)
    client = _client()
    try:
        if slug:
            artifact = client.update_artifact(slug, title=title, content=content, tags=tags)
            if visibility == "unlisted" and not artifact.get("share_url"):
                artifact = client.share_artifact(slug) or artifact
            elif visibility == "private" and artifact.get("share_url"):
                client.share_artifact(slug, enable=False)
                artifact = client.get_artifact(slug)
            return artifact
        return client.create_artifact(title, content, visibility, tags=tags)
    finally:
        client.close()


@mcp.tool()
def list_artifacts() -> list[dict]:
    """List the artifacts owned by the configured token."""
    client = _client()
    try:
        return client.list_artifacts()
    finally:
        client.close()


@mcp.tool()
def get_artifact(slug: str) -> dict:
    """Fetch one artifact: source Markdown, rendered HTML and plain text."""
    client = _client()
    try:
        return client.get_artifact(slug)
    finally:
        client.close()


@mcp.tool()
def update_artifact(
    slug: str,
    title: str | None = None,
    content: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Change an artifact's title, content and/or tags. The slug never changes."""
    client = _client()
    try:
        return client.update_artifact(slug, title=title, content=content, tags=tags)
    finally:
        client.close()


@mcp.tool()
def list_tags() -> list[dict]:
    """List the tag vocabulary owned by the configured token (name, slug, count)."""
    client = _client()
    try:
        return client.list_tags()
    finally:
        client.close()


@mcp.tool()
def delete_tag(tag: str) -> dict:
    """Delete a tag from the vocabulary by its slug, detaching it everywhere."""
    client = _client()
    try:
        client.delete_tag(tag)
        return {"slug": tag, "deleted": True}
    finally:
        client.close()


@mcp.tool()
def delete_artifact(slug: str) -> dict:
    """Delete an artifact by slug."""
    client = _client()
    try:
        client.delete_artifact(slug)
        return {"slug": slug, "deleted": True}
    finally:
        client.close()


@mcp.tool()
def share_artifact(slug: str, enable: bool = True) -> dict:
    """Enable (``enable=True``) or revoke (``enable=False``) the unlisted share link.

    Enabling returns the artifact with a ``share_url``; revoking clears it.
    """
    client = _client()
    try:
        if enable:
            return client.share_artifact(slug) or {}
        client.share_artifact(slug, enable=False)
        return {"slug": slug, "share_url": None}
    finally:
        client.close()


@mcp.resource(
    "pullini://skill",
    name="pullini-skill",
    title="Pullini artifacts skill",
    description="Agent skill describing how to use the Pullini MCP artifact tools.",
    mime_type="text/markdown",
)
def skill() -> str:
    """Return the local agent skill describing the MCP tools."""
    return files("pullini_mcp").joinpath("skill.md").read_text(encoding="utf-8")


def main() -> None:
    """Run the stdio server (entry point for ``uvx pullini-mcp``)."""
    mcp.run()


if __name__ == "__main__":
    main()
