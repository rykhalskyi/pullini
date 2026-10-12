"""URL configuration for the artifacts app (owner routes and ``/a/`` shares)."""

from __future__ import annotations

from django.urls import path

from pullini.artifacts import views

app_name = "artifacts"

urlpatterns = [
    path("artifacts/", views.artifact_list, name="list"),
    path("artifacts/<slug:slug>/tags/", views.tag_add, name="tag_add"),
    path("artifacts/<slug:slug>/tags/<str:tag>/remove/", views.tag_remove, name="tag_remove"),
    path("artifacts/<slug:slug>/", views.artifact_detail, name="detail"),
    path("tags/<str:tag>/delete/", views.tag_delete, name="tag_delete"),
    path("a/<str:share_token>/", views.artifact_shared, name="shared"),
]
