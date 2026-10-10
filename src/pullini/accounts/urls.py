"""URL configuration for the accounts app (mounts under ``/settings/``)."""

from __future__ import annotations

from django.urls import path

from pullini.accounts import views

app_name = "accounts"

urlpatterns = [
    path("tokens/", views.token_list, name="tokens"),
    path("tokens/create/", views.token_create, name="token_create"),
    path("tokens/<int:token_id>/revoke/", views.token_revoke, name="token_revoke"),
]
