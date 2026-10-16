"""Rename duplicate project slugs before the global unique index is added (T15).

Slugs were unique only per owner; the schema migration that follows makes them
globally unique. This de-duplicates any existing collisions deterministically
(earliest ``pk`` keeps the slug, later ones get a ``-2``/``-3`` suffix).
"""

from __future__ import annotations

from django.db import migrations
from django.utils.text import slugify


def dedupe_slugs(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    seen: set[str] = set()
    for project in Project.objects.order_by("pk"):
        base = project.slug or slugify(project.name) or "project"
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}-{suffix}"
            suffix += 1
        if candidate != project.slug:
            project.slug = candidate
            project.save(update_fields=["slug"])
        seen.add(candidate)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0006_alter_project_update_interval_minutes"),
    ]

    operations = [
        migrations.RunPython(dedupe_slugs, noop),
    ]
