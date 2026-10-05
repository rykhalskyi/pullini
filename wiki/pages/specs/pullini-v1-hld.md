---
created: 2026-09-30
type: spec
status: proposed
summary: V1 high-level design for Pullini, a read-only Git-backed wiki browser (Python/Django monolith).
---

# Pullini V1 — High-Level Design

See also: [project overview](../project-overview.md) · [build & deploy](../build-deploy.md)

## 1. Product

**Pullini** is a read-only Git-backed wiki browser.

> **Git is the source of truth. Pullini makes Git-based documentation easy to browse and search.**

Wiki content is never edited in Pullini.

## 2. Architecture

**Python monolith web application**

```text
Browser
   │
   ▼
Pullini Web App
   ├── UI / UX
   ├── Authentication
   ├── Project management
   ├── Git synchronization
   ├── Markdown/page generation
   └── Search/indexing
          │
          ├── Database
          └── Local Git repositories
```

Recommended stack:

* Python
* Django
* Django Templates + HTMX
* Tailwind CSS
* SQLite or PostgreSQL
* Git CLI / Git library
* Markdown renderer
* Full-text/search index

No microservices in V1.

## 3. Installation types

### A. Docker Compose

Self-contained installation for simple deployments.

```text
Pullini
├── Web application
├── SQLite
└── Persistent data / Git repositories
```

PostgreSQL should remain an optional configuration.

### B. Kubernetes / k3s + FluxCD

GitOps-driven deployment.

```text
FluxCD
   │
   ▼
k3s
   │
   ├── Pullini
   └── PostgreSQL (existing cluster service)
```

Pullini should support PostgreSQL through configuration.

The application should not depend on the installation type.

## 4. Authentication / users

V1 has two roles: **Admin** (staff) and a non-staff **reader** (D-27).

Admin can:

* Log in
* View all projects
* Add projects
* Configure projects
* Delete projects
* Trigger project refresh
* Browse/search all documentation

Admin cannot:

* Edit wiki pages
* Create wiki pages
* Delete wiki pages
* Modify Git content through Pullini

A **reader** can log in, browse and search all public documentation, and keep
per-user state such as favorites. A reader cannot manage projects.

All wiki pages are **public/read-only**.

## 5. Projects

A Pullini project represents a Git repository and its documentation.

Project configuration:

```text
Project
├── Name
├── Git repository URL
├── Branch
├── Wiki/documentation folder
├── Update interval
└── Enabled/status
```

Example:

```text
Payments
  Repository: https://git.example.com/payments.git
  Branch: main
  Folder: /docs
  Update: every 10 minutes
```

Default update interval:

**10 minutes**

Admin can configure the interval.

## 6. Git synchronization

Each project has a **persistent local clone** of its configured Git repository.

Pullini does not need Git history.

The local repository is treated as a **working-state/cache**.

Conceptually:

```text
Remote Git repository
        │
        │ clone / pull
        ▼
Local project state
        │
        ▼
Wiki page generation
        │
        ▼
Search index
```

Only the configured:

* repository
* branch
* folder

are relevant to wiki generation.

Git history is not exposed or required by Pullini V1.

## 7. Synchronization

Projects are automatically updated on the configured schedule.

Default:

**Every 10 minutes**

Admin can also trigger:

**Refresh now**

After a successful pull/update:

```text
Git update
    ↓
Detect changed content
    ↓
Regenerate affected wiki pages
    ↓
Update search index
    ↓
UI shows latest content
```

The UI should clearly expose:

* Last successful update
* Current sync status
* Last error, if any
* Next scheduled update

## 8. Wiki generation

Pullini reads the configured documentation folder and generates read-only wiki pages.

Supported V1 content should be kept intentionally focused, e.g.:

* Markdown
* Headings
* Links
* Images/assets
* Code blocks
* Tables
* Lists

The original Git files remain authoritative.

Pullini generates the **presentation**, not the content.

## 9. Search

Search is a first-class feature.

### Scopes

At minimum:

```text
Search
├── Current project
└── All projects
```

Potential additional scope:

```text
Current section
```

Search should cover:

* Page titles
* Page content
* Headings
* Paths
* Project names

Search should provide contextual snippets and identify the project/page location.

Example:

```text
Authentication
Payments / Security

How API authentication works...
```

### Smart indexing

The search index is updated when project content changes.

Avoid requiring Elasticsearch/OpenSearch in V1.

Use database-native/full-text search where practical:

* SQLite FTS5
* PostgreSQL full-text search

The search implementation should be abstracted enough to support both installation types.

## 10. UX / UI

The UI should be **read-first and content-first**.

Global navigation:

```text
Pullini

🔍 Search

PROJECTS
  Payments
  Mobile
  Infrastructure

+ Add project

Settings
```

Project navigation:

```text
Project

Overview
Wiki
Activity
```

Wiki navigation:

```text
Wiki

[ Tree ] [ Index ] [ Recent ]
```

### Tree

Repository/documentation hierarchy.

### Index

Flat searchable/ordered page catalogue.

### Recent

Recently updated pages.

### Page

Clean documentation-reading experience with:

* Breadcrumbs
* Page title
* Content
* Navigation
* Source/path information
* Last update information

No editing controls.

## 11. Project overview

Each project should expose:

* Project description/name
* Page count
* Wiki structure
* Recently updated pages
* Git source
* Sync status
* Last update

The Git source should be clearly visible but secondary to the documentation.

## 12. Activity

Activity is **read-only Git-derived information**.

Show things such as:

* Updated pages
* Update time
* Synchronization status
* Relevant Git revision/commit identifier

Pullini does not need to provide a Git diff viewer in V1.

## 13. Data model

Minimal application state:

```text
User
Project
ProjectSyncState
Page/SearchIndex
```

Git remains the source of truth for page content.

Database stores:

* Admin account
* Project configuration
* Sync state
* Page/index metadata
* Search index

The database is **not the canonical wiki content store**.

## 14. Persistence

Persistent data must survive application restarts.

Docker Compose:

```text
/data
├── database
└── repositories
```

Kubernetes:

* Persistent volume for Pullini state/repositories
* PostgreSQL for application data
* Configuration/secrets supplied through Kubernetes/FluxCD

## 15. Operational requirements

V1 should expose basic health/status information:

```text
Application: Healthy
Database: Connected
Git: Available
Projects: 5
Last sync: 2 min ago
```

Project synchronization errors must not make the whole application unavailable.

A failed project sync should leave the **last successfully generated content available** and show the project as having a sync error.

## V1 principles

1. **Git is the source of truth.**
2. **Pullini is read-only for wiki content.**
3. **One admin user.**
4. **Projects are the primary organizational unit.**
5. **Search is first-class.**
6. **Automatic synchronization, default 10 minutes.**
7. **Manual refresh is always available.**
8. **No Git history is required.**
9. **Simple Python monolith.**
10. **SQLite for easy Compose deployment; PostgreSQL for k3s/production.**
11. **No microservices or unnecessary infrastructure.**
12. **Public pages, simple administration.**

## Main V1 flow

```text
                 Git repository
                       │
                       │ scheduled/manual refresh
                       ▼
                 Local project
                       │
                       ▼
                Markdown parsing
                       │
                ┌──────┴──────┐
                ▼             ▼
          Wiki generation   Search index
                │             │
                └──────┬──────┘
                       ▼
                    Pullini
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
       Browse                    Search
          │                         │
          └──────────┬──────────────┘
                     ▼
                  Read-only
                   pages
```

The resulting V1 is deliberately small: **one monolith, one admin, projects backed by Git, automatic synchronization, generated read-only pages, and strong search/navigation.**
