"""Public account URLs: password setup links are reachable without logging in."""

from __future__ import annotations

from django.urls import path

from pullini.accounts import views

urlpatterns = [
    path(
        "set-password/<uidb64>/<token>/",
        views.password_setup,
        name="password_setup",
    ),
]
