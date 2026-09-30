"""Root URL configuration for Pullini."""

from __future__ import annotations

from django.contrib import admin
from django.urls import path

from pullini.core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz", views.healthz, name="healthz"),
    path("admin/", admin.site.urls),
]
