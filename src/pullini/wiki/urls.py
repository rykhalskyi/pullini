"""URL configuration for the wiki app (mounted under ``projects/``)."""

from __future__ import annotations

from django.urls import path

from pullini.wiki import views

app_name = "wiki"

urlpatterns = [
    path("<slug:slug>/wiki/", views.wiki_tree, name="tree"),
    path("<slug:slug>/wiki/index/", views.wiki_index, name="index"),
    path("<slug:slug>/wiki/recent/", views.wiki_recent, name="recent"),
    path("<slug:slug>/wiki/assets/<path:asset_path>", views.wiki_asset, name="asset"),
    path("<slug:slug>/wiki/<path:page_path>/", views.wiki_page, name="page"),
]
