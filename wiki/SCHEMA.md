# Wiki Schema

Conventions for the Pullini project wiki. Kept in `wiki/`, version-controlled with the code.

**Design goal: token-lean.** Git is the change history; the wiki stores current knowledge and decisions.

## Token discipline

1. **Git is the history.** No `## Updates` sections, no "Created <date>" in index entries, no restating superseded content.
2. **One page per work item by default.** A ticket page carries `## Spec`, `## Plan`, and `## Outcome`. Separate `specs/` + `plans/` pages only for large/ambiguous epics.
3. **Decisions get a one-liner** in `decisions.md`; reference the id (`D-07`) from the ticket instead of restating rationale.
4. **Minimal frontmatter:** `created`, `type`, `status`, `summary`. No `tags`, no `related`.
5. **Never hand-edit `index.md`.** Regenerate with `node scripts/wiki.mjs index`.
6. **Keep `AGENTS.md` short**; detail lives here.

## Layout

```text
wiki/
├── AGENTS.md      # short, always-loaded summary
├── SCHEMA.md      # this file
├── index.md       # generated catalog — never edit by hand
├── log.md         # append-only activity log
├── decisions.md   # append-only decision record (ADR-lite)
└── pages/
    ├── project-overview.md
    ├── build-deploy.md
    ├── epics/                # large features broken into tickets
    ├── tickets/              # default artifact per work item
    ├── specs/                # only for large/ambiguous epics
    ├── plans/                # only for large/ambiguous epics
    └── research/             # investigations and analysis
```

## Frontmatter

```yaml
---
created: YYYY-MM-DD
type: overview | build-deploy | epic | ticket | spec | plan | research
status: proposed | in-progress | implemented | superseded   # when meaningful
summary: One-line description used to build index.md
---
```

`created` never changes. `summary` is required on new pages.

## Links

Relative markdown links — **never wikilinks**. Paths are relative to the file containing the link.

| From | To | Link |
|---|---|---|
| `wiki/index.md` | any page | `pages/<folder>/<slug>.md` |
| `pages/<sub>/x.md` | `pages/<other>/y.md` | `../<other>/y.md` |
| `pages/<sub>/x.md` | `pages/root-page.md` | `../root-page.md` |
| `pages/root-page.md` | `pages/<folder>/y.md` | `<folder>/y.md` |

## Slugs

- Tickets: `<ticket-id>-<brief>` (e.g. `ticket-15-localization-infra`).
- Specs and plans share one `<feature-slug>` so they cross-link.
- Research: `<topic>`, lowercase, hyphen-separated.

## Workflows

### Ticket

1. Create `pages/tickets/<slug>.md` with `created`, `type: ticket`, `status`, `summary`.
2. Body: title, link to epic/spec/plan if any, then `## Spec`, `## Plan`, `## Outcome`.
3. `node scripts/wiki.mjs index`, then `node scripts/wiki.mjs log ticket "<title>"`.

### Spec / Plan (large epics only)

Create `pages/specs/<slug>.md` and/or `pages/plans/<slug>.md`, cross-link, regenerate index, log.

### Research

Create `pages/research/<slug>.md` (context, findings, conclusions, recommended actions); regenerate index; log.

### Decision

```bash
node scripts/wiki.mjs decision "<decision> — because <reason>"
```

Appends `- [YYYY-MM-DD] D-nn — <decision> — because <reason>` to `decisions.md`.

### Operations

```bash
node scripts/wiki.mjs index    # rewrite index.md from page summaries
node scripts/wiki.mjs log <action> "<description>"
node scripts/wiki.mjs lint     # missing frontmatter, dangling links, unindexed pages
```

### Update

Edit the page directly — no `## Updates` section (use git). Regenerate the index if the summary changed and log with `wiki.mjs log update "<page> — <note>"`.
