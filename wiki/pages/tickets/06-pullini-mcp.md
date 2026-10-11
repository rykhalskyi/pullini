---
created: 2026-10-08
type: ticket
status: implemented
summary: T6 — pullini-mcp: a local stdio FastMCP connector on PyPI that calls the artifact REST API with a PAT.
---

# T6 — pullini-mcp Connector

Part of [E6 — User Artifacts & Agent Connector (MCP)](../epics/epic-06-user-artifacts-and-mcp.md).
Calls [T5 — Artifact REST API](05-artifact-rest-api.md) with a
[T3 — Personal Access Token](03-personal-access-tokens.md).

## Spec

Ship `pullini-mcp`, a local **stdio** MCP server that translates MCP tool calls
into authenticated HTTPS requests to the Pullini host (D-25, D-33). It runs on the
agent's machine, reads configuration from the environment
(`PULLINI_URL`, `PULLINI_TOKEN`) and needs no ASGI or OAuth infrastructure on the
server.

Tools exposed:

```text
store_artifact   create or overwrite an artifact
list_artifacts   list the user's artifacts
get_artifact     fetch one artifact (source Markdown)
update_artifact  change title/content
delete_artifact  remove an artifact
share_artifact   enable/revoke the unlisted share link
```

The package lives in this repository under `mcp/` and is published to PyPI via
Trusted Publishing so users can run `uvx pullini-mcp` (D-33).

Out of scope: remote HTTP MCP transport, OAuth 2.1, ASGI hosting, non-artifact
tools.

## Plan

1. `mcp/` subdirectory with its own `pyproject.toml` (`name = "pullini-mcp"`, deps
   `mcp`/`fastmcp` + `httpx`), `src/pullini_mcp/{__init__.py,server.py,client.py}`.
2. `client.py`: thin HTTP client over the T5 API reusing `PULLINI_URL` /
   `PULLINI_TOKEN`, mapping HTTP errors to readable tool errors.
3. `server.py`: MCP stdio server registering the six tools above. (`mcp` 2.x
   renamed `FastMCP` to `MCPServer`; the connector uses the current class.)
4. `mcp/README.md`: install (`uvx pullini-mcp`), env vars, and client config
   snippets for common MCP clients.
5. `.github/workflows/publish-mcp.yml`: build + publish on tag using PyPI Trusted
   Publishing (`id-token: write`, `pypi` environment) — no stored secrets.
6. Tests under `mcp/tests/` using a mocked HTTP client; run with `uv run pytest`.
7. Regenerate the wiki index; record D-33.

## Decisions

D-25 local stdio connector on PyPI · D-33 in-repo `mcp/` package with Trusted
Publishing.

## Outcome

Shipped. The `mcp/` subdirectory is its own `pullini-mcp` project (hatchling,
`mcp>=2` + `httpx`) under `src/pullini_mcp/`:
- `client.py`: `Config.from_env` (`PULLINI_URL`, `PULLINI_TOKEN`, trailing slash
  trimmed) and `PulliniClient` — a thin `httpx` wrapper over the T5 endpoints
  (`me`, `list/get/create/update/delete_artifact`, `share_artifact`) mapping
  non-2xx responses and transport failures to readable `PulliniError`s.
- `server.py`: `MCPServer("pullini")` (the mcp 2.x name for `FastMCP`) exposing
  `store_artifact`, `list_artifacts`, `get_artifact`, `update_artifact`,
  `delete_artifact`, `share_artifact`; each opens a client from the environment
  per call. `main()` runs the default stdio transport.
- `README.md`: `uvx pullini-mcp` install, env vars, and a client-config snippet.
- `pyproject.toml`: `pullini-mcp = "pullini_mcp.server:main"` console script.

Publishing: `.github/workflows/publish-mcp.yml` builds `mcp/` and publishes on
`mcp-v*` tags via PyPI Trusted Publishing (OIDC, `pypi` environment, no secrets).
CI: a `mcp` job in `ci.yml` runs ruff + pytest in `mcp/`.

Verification: `uv run pytest` in `mcp/` → 20 passed (mocked `httpx.MockTransport`,
no live host); `ruff check`/`format` clean; `uv build` produces the sdist and
wheel; the six tools register on `mcp.list_tools()`.
