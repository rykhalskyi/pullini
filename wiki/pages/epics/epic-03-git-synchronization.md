---
created: 2026-09-30
type: epic
status: implemented
summary: E3 — Git sync: shallow per-project clones, scheduled + manual refresh, sync state, resilient failures.
---

# E3 — Git Synchronization

Design: [Pullini V1 — High-Level Design](../specs/pullini-v1-hld.md) (§6, §7, §15).
Builds on [E2 — Admin & Projects](epic-02-admin-and-projects.md).

## Spec

Each project keeps a **persistent shallow clone** under
`DATA_DIR/repositories/<slug>` and is refreshed on its own interval (default 10
minutes) or on demand. Pullini needs the working tree, not history. A failed
sync must not take the app down and must leave the last good clone in place
(HLD §15). Out of scope: page generation (E4), search (E5).

## Plan

1. `ProjectSyncState` model: status, last commit, last attempt/success, last error.
2. `projects/git.py`: Git CLI wrapper (shallow single-branch clone, fetch+reset).
3. `projects/sync.py`: per-project file lock, due-time logic, error capture.
4. `manage.py sync_projects` (scheduler entry point; `--force`, `--project`).
5. **Refresh now**: admin changelist action, a staff-only button on the project
   page and on the admin change form (`POST /projects/<slug>/refresh/`), plus a
   sync status column.
6. `/healthz` reports the most recent successful sync.
7. Scheduler: Compose `scheduler` service + k8s sidecar (CronJob dropped).
8. Tests against a local bare repo fixture (no network).

## Outcome

Shipped. `uv run pytest` → 36 passed; ruff clean; `docker compose config` and
`kubectl kustomize k8s` valid.

Key files:

- [`src/pullini/projects/git.py`](../../../src/pullini/projects/git.py)
- [`src/pullini/projects/sync.py`](../../../src/pullini/projects/sync.py)
- [`src/pullini/projects/management/commands/sync_projects.py`](../../../src/pullini/projects/management/commands/sync_projects.py)
- [`docker/scheduler.sh`](../../../docker/scheduler.sh)

Deviations: the k8s scheduler is a **sidecar container**, not the CronJob
sketched in E1, because the clone lives on a ReadWriteOnce volume (see D-15).
Change detection currently records the resolved commit; triggering page
regeneration is E4.

## Decisions

D-14 Git CLI over a Git library · D-15 scheduler as sidecar, not CronJob ·
D-16 per-project `flock`. See [`decisions.md`](../../decisions.md).

## Next

E4 — Wiki generation.
