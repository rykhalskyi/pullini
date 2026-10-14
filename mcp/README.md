# pullini-mcp

A local **stdio** [MCP](https://modelcontextprotocol.io) connector that lets an
agent create, read, update, delete and share [Pullini](https://github.com/rykhalskyi/pullini)
artifacts, and generate self-study quizzes and static Q&A sets about wiki pages or
artifacts, over the authenticated artifact REST API.

The connector runs on the agent's machine. It reads its configuration from the
environment and needs no ASGI or OAuth infrastructure on the Pullini host
(decision D-25).

## Install

Runs with [uv](https://docs.astral.sh/uv/), no install step required:

```bash
uvx pullini-mcp
```

Or install it into an environment:

```bash
uv tool install pullini-mcp   # or: pip install pullini-mcp
```

## Configure

Two environment variables:

| Variable        | Description                                                        |
| --------------- | ------------------------------------------------------------------ |
| `PULLINI_URL`   | Base URL of your Pullini host, e.g. `https://pullini.example.com`. |
| `PULLINI_TOKEN` | A personal access token created at `/settings/tokens/` (`pln_…`).  |

The token is sent as `Authorization: Bearer <token>`; all resources are scoped to
the token's owner. Treat the raw secret like a password.

### MCP client config

The client launches the server and passes the two variables. The examples below
are for [opencode](https://opencode.ai) (`opencode.jsonc`); adapt the shape to
your own MCP client. The same example lives in
[`mcp.example.json`](mcp.example.json).

**From a local checkout** (before the package is published): point `--directory`
at the `mcp/` folder of your clone.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "pullini": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/path/to/pullini/mcp", "pullini-mcp"],
      "enabled": true,
      "environment": {
        "PULLINI_URL": "http://localhost:8000",
        "PULLINI_TOKEN": "pln_xxxxxxxx_yyyyyyyyyyyyyyyyyyyyyyyy"
      }
    }
  }
}
```

**From PyPI** (once published):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "pullini": {
      "type": "local",
      "command": ["uvx", "pullini-mcp"],
      "enabled": true,
      "environment": {
        "PULLINI_URL": "https://pullini.example.com",
        "PULLINI_TOKEN": "pln_xxxxxxxx_yyyyyyyyyyyyyyyyyyyyyyyy"
      }
    }
  }
}
```

## Tools

| Tool              | What it does                                                   |
| ----------------- | -------------------------------------------------------------- |
| `store_artifact`  | Create an artifact, or overwrite one when `slug` is given.     |
| `list_artifacts`  | List the token owner's artifacts.                              |
| `get_artifact`    | Fetch one artifact (source Markdown, rendered HTML, plain text). |
| `update_artifact` | Change an artifact's title and/or content.                     |
| `delete_artifact` | Delete an artifact.                                            |
| `share_artifact`  | Enable or revoke the unlisted share link.                      |
| `list_pages`      | List readable wiki pages, optionally for one project.          |
| `get_page`        | Fetch one wiki page's source Markdown.                         |
| `create_quiz`     | Create or replace a quiz for one page or artifact.             |
| `get_quiz`        | Fetch one quiz (questions and your scores).                    |
| `list_quizzes`    | List the token owner's quizzes.                                |
| `delete_quiz`     | Delete a quiz.                                                 |
| `create_qanda`    | Create or replace a static Q&A set for one page or artifact.   |
| `get_qanda`       | Fetch one Q&A set (questions and answers).                     |
| `list_qanda`      | List the token owner's Q&A sets.                               |
| `delete_qanda`    | Delete a Q&A set.                                              |

`content` is Markdown; fenced ` ```mermaid ` blocks render as diagrams. Artifacts
are **private by default**: `share_artifact` returns a read-only `share_url`
anyone with the link can open, and revoking clears it.

Quizzes are private and self-study: fetch a page with `get_page`, write up to 10
multiple-choice questions and pass them to `create_quiz` with either a
`page={"project", "path"}` or an `artifact` slug target. Creating again for the
same target replaces it; read scores back from `get_quiz`/`list_quizzes`.

Q&A sets are private, static FAQs: write up to 50 `{question, answer}` entries and
pass them to `create_qanda` with a `page` or `artifact` target. Answers are
Markdown, rendered read-only; nothing is scored. Creating again for the same target
replaces it; read sets back from `get_qanda`/`list_qanda`.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

Tests mock the HTTP transport with `httpx.MockTransport`, so no Pullini host is
needed.
