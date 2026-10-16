"""Assign existing ownerless projects to the earliest superuser (T15).

Before T15 projects had no owner. After adding the ``user`` field, any project
that predates it is handed to the first superuser (the admin), matching the
single-admin deployment model (D-35).
"""

from __future__ import annotations

from django.conf import settings
from django.db import migrations


def assign_owner(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    owner = User.objects.filter(is_superuser=True).order_by("pk").first()
    if owner is not None:
        Project.objects.filter(user__isnull=True).update(user=owner)


def unassign_owner(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    User = apps.get_model(settings.AUTH_USER_MODEL)
    owner = User.objects.filter(is_superuser=True).order_by("pk").first()
    if owner is not None:
        Project.objects.filter(user=owner).update(user=None)


class Migration(migrations.Migration):
    dependencies = [
        ("projects", "0003_project_owner"),
    ]

    operations = [
        migrations.RunPython(assign_owner, unassign_owner),
    ]
