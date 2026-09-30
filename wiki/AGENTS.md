# Wiki

Project knowledge base for Pullini, under `wiki/`. Read `wiki/index.md` first, then drill into pages.

- **History is git** — never add "Updates" sections or dates to index entries.
- **One page per work item**: `wiki/pages/tickets/<slug>.md` with `## Spec` / `## Plan` / `## Outcome`. Specs/plans only for large epics.
- **Never hand-edit** `wiki/index.md` — regenerate it.
- Helper: `node scripts/wiki.mjs <index|log|decision|lint>`.

```bash
node scripts/wiki.mjs index                    # regenerate index.md
node scripts/wiki.mjs log ticket "<title>"     # append to log.md
node scripts/wiki.mjs decision "<what> — because <why>"
node scripts/wiki.mjs lint
```

Full conventions: [SCHEMA.md](SCHEMA.md). Key design: [project overview](pages/project-overview.md) · [V1 HLD](pages/specs/pullini-v1-hld.md).
