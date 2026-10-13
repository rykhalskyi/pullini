"""URL configuration for the quizzes app (owner routes)."""

from __future__ import annotations

from django.urls import path

from pullini.quizzes import views

app_name = "quizzes"

urlpatterns = [
    path("quizzes/<int:pk>/", views.quiz_detail, name="detail"),
    path("quizzes/<int:pk>/submit/", views.quiz_submit, name="submit"),
]
