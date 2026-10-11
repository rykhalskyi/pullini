"""Root URL configuration for Pullini."""

from __future__ import annotations

from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from pullini.core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("healthz", views.healthz, name="healthz"),
    path("livez", views.livez, name="livez"),
    path("projects/", include("pullini.projects.urls")),
    path("projects/", include("pullini.wiki.urls")),
    path("search/", include("pullini.search.urls")),
    path("favorites/", include("pullini.favorites.urls")),
    path("settings/", include("pullini.accounts.urls")),
    path("admin/", admin.site.urls),
]
