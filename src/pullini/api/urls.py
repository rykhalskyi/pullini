"""Root URL aggregator for the authenticated JSON API (E6, T5)."""

from __future__ import annotations

from django.urls import path

from pullini.accounts import api as accounts_api
from pullini.artifacts import api as artifacts_api

app_name = "api"

urlpatterns = [
    path("me/", accounts_api.me, name="me"),
    path("skill/", artifacts_api.skill, name="skill"),
    path("artifacts/", artifacts_api.artifact_collection, name="artifact_collection"),
    path("artifacts/<slug:slug>/", artifacts_api.artifact_item, name="artifact_item"),
    path("artifacts/<slug:slug>/share/", artifacts_api.artifact_share, name="artifact_share"),
]
