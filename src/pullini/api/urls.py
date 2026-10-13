"""Root URL aggregator for the authenticated JSON API (E6, T5)."""

from __future__ import annotations

from django.urls import path

from pullini.accounts import api as accounts_api
from pullini.artifacts import api as artifacts_api
from pullini.quizzes import api as quizzes_api

app_name = "api"

urlpatterns = [
    path("me/", accounts_api.me, name="me"),
    path("skill/", artifacts_api.skill, name="skill"),
    path("artifacts/", artifacts_api.artifact_collection, name="artifact_collection"),
    path("artifacts/<slug:slug>/", artifacts_api.artifact_item, name="artifact_item"),
    path("artifacts/<slug:slug>/share/", artifacts_api.artifact_share, name="artifact_share"),
    path("tags/", artifacts_api.tag_collection, name="tag_collection"),
    path("tags/<str:slug>/", artifacts_api.tag_item, name="tag_item"),
    path("quizzes/", quizzes_api.quiz_collection, name="quiz_collection"),
    path("quizzes/<int:pk>/attempts/", quizzes_api.quiz_attempt, name="quiz_attempt"),
    path("quizzes/<int:pk>/", quizzes_api.quiz_item, name="quiz_item"),
    path("pages/", quizzes_api.page_collection, name="page_collection"),
    path("pages/<slug:project>/<path:page_path>/", quizzes_api.page_item, name="page_item"),
]
