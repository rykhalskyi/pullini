"""URL configuration for the projects app."""

from __future__ import annotations

from django.urls import path

from pullini.projects import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("manage/", views.project_manage, name="manage"),
    path("create/", views.project_create, name="create"),
    path("<slug:slug>/refresh/", views.project_refresh, name="refresh"),
    path("<slug:slug>/delete/", views.project_delete, name="delete"),
    path("<slug:slug>/", views.project_detail, name="detail"),
]
