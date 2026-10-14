"""URL configuration for the Q&A app (owner routes)."""

from __future__ import annotations

from django.urls import path

from pullini.qanda import views

app_name = "qanda"

urlpatterns = [
    path("qanda/<int:pk>/", views.qanda_detail, name="detail"),
]
