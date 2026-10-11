"""Tests for the MCP instructions page and its navigation entry."""

from __future__ import annotations

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_mcp_page_renders_instructions(client):
    response = client.get(reverse("mcp"))

    assert response.status_code == 200
    body = response.content.decode()
    assert "pullini-mcp" in body
    assert "PULLINI_TOKEN" in body
    assert "PyPI" in body
    assert "in progress" in body


def test_home_menu_links_to_mcp(client):
    body = client.get(reverse("home")).content.decode()

    assert f'href="{reverse("mcp")}"' in body
