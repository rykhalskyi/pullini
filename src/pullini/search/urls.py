"""URL configuration for search (mounted under ``search/``)."""

from __future__ import annotations

from django.urls import path

from pullini.search import views

app_name = "search"

urlpatterns = [
    path("", views.global_search, name="global"),
    path("<slug:slug>/", views.project_search, name="project"),
]
