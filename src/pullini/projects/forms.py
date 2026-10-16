"""Project management form for the in-app owner page (T15).

Mirrors the fields an owner may configure; the owner is assigned by the view,
not chosen here.
"""

from __future__ import annotations

from django import forms

from pullini.projects.models import Project

_INPUT = (
    "w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-navy "
    "focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/30"
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = (
            "name",
            "description",
            "repo_url",
            "branch",
            "docs_folder",
            "update_interval_minutes",
            "enabled",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT}),
            "description": forms.Textarea(attrs={"class": _INPUT, "rows": 3}),
            "repo_url": forms.TextInput(attrs={"class": _INPUT}),
            "branch": forms.TextInput(attrs={"class": _INPUT}),
            "docs_folder": forms.TextInput(attrs={"class": _INPUT}),
            "update_interval_minutes": forms.NumberInput(attrs={"class": _INPUT}),
            "enabled": forms.CheckboxInput(
                attrs={"class": "size-4 rounded border-line text-brand focus:ring-brand/30"}
            ),
        }
