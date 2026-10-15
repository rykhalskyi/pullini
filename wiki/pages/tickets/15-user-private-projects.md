---
created: 2026-10-15
type: ticket
status: proposed
summary: T15 — user-owned private projects: owner-scoped visibility, an in-app management page, per-user slugs + namespaced clones, superuser oversight and cascade cleanup.
---

# T15 — User-owned private projects

Related: [V1 HLD §4/§5](../specs/pullini-v1-hld.md) ·
[E2 — Admin & Projects](../epics/epic-02-admin-and-projects.md) ·
supersedes parts of D-12 and the public-read model of D-03/D-27.

## Spec

Today every project is ownerless and every wiki page is public (D-03, D-27,
HLD §4). This ticket makes a project **owned by one user and private to that
owner**: only the owner and superusers can browse it and its pages; other users
and anonymous visitors get 404. Non-admin users add and delete their own
projects through a new in-app management page (not the Django admin); superusers
see and delete every project. Deleting a user removes all of their content and
clones.

Locked decisions:

- Visibility is **owner-private**; no sharing/unlisted links in this change.
- **`is_superuser`** grants cross-user visibility and deletion (consistent with
  D-35); `is_staff` does not.
- Slug **and** name are unique **per owner** (like artifacts, D-31); clone and
  lock paths are namespaced by owner.
- Existing (ownerless) projects are assigned to the earliest superuser in a data
  migration.
- Creating a project triggers an inline `sync_project(force=True)`; failures are
  tolerated and surfaced to the owner.
- Management is **web-UI only**; no REST/MCP project CRUD.
- Cascade: deleting the owner deletes projects, pages, quizzes, Q&A, favorites,
  sync state, and the on-disk clone.

Out of scope: sharing links, per-project membership/teams, self-signup (users are
assumed provisioned by the admin), REST/MCP project endpoints, Git history/diff.

Open items: confirm self-signup is out of scope; decide whether to ship a one-off
clone-relocation command or accept re-cloning into the new path.

## Plan

Data model (`projects/models.py` + migration `0003`):

1. Add `user` FK (`AUTH_USER_MODEL`, `CASCADE`, `related_name="projects"`,
   `null=True`).
2. Drop global `unique` on `name`/`slug`; add per-user unique constraints
   `(user, slug)` and `(user, name)` plus index `(user, name)`; scope
   `_unique_slug` to the owner.
3. Data migration assigns ownerless projects to the earliest superuser.

Access (`projects/access.py`):

4. `visible_projects(user)`: superuser → all; authenticated → `filter(user=user)`;
   anonymous → none.
5. `can_manage(user, project)`: superuser or owner.

Storage (`projects/sync.py` + signal):

6. `repository_path`/`_lock_path` → `REPOSITORIES_DIR/<user_id>/<slug>`.
7. `post_delete` signal removes the clone dir + lock on `transaction.on_commit`.

Web management:

8. `projects/forms.py`: `ProjectForm` (name, description, repo_url, branch,
   docs_folder, update_interval_minutes, enabled).
9. Views: `project_manage` (GET), `project_create` (POST, owner + inline sync),
   `project_delete` (POST, owner/superuser); relax `project_refresh` to
   `can_manage`.
10. URLs ordered before the `<slug:slug>/` catch-all; template
    `projects/manage.html`; nav + home links.

Cross-cutting:

11. Search backends scope page queries to `visible_projects(user)`; thread `user`
    through the service.
12. Home uses `visible_projects`; `ProjectAdmin` gains `user` in
    display/filter/fieldsets.

Tests:

13. Update `conftest` fixtures to create + assign an owner and log in; rewrite
    public-visibility tests for owner-private semantics; add owner isolation,
    superuser oversight, per-user slug, cascade (user delete removes
    project/pages/clone), manage add/delete, owner refresh.

Wiki/docs:

14. Update HLD §4/§5 and project-overview; add decisions; this ticket; regenerate
    index; log.

## Decisions

To be recorded with `wiki.mjs decision`:

- Projects are user-owned and owner-private (owner + superusers only);
  anonymous/other users get 404 — because users need private documentation
  workspaces (extends the artifact model to projects).
- The superuser flag, not `is_staff`, grants cross-user project visibility and
  deletion — because admin is the single superuser (D-35).
- Project slug/name are unique per owner and clone/lock paths are namespaced by
  owner — because two users may pick the same project name.
- Project management moves from the Django admin to an in-app page (supersedes
  D-12) — because non-admin owners must manage their own projects without admin
  access.

## Outcome

Not started.
