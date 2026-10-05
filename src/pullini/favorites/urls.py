"""URL configuration for the favorites app."""

from __future__ import annotations

from django.urls import path

from pullini.favorites import views

app_name = "favorites"

urlpatterns = [
    path("", views.favorites_list, name="list"),
    path("toggle/<int:page_id>/", views.favorite_toggle, name="toggle"),
]
