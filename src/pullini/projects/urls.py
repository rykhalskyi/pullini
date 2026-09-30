"""URL configuration for the projects app."""

from __future__ import annotations

from django.urls import path

from pullini.projects import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("<slug:slug>/", views.project_detail, name="detail"),
]
