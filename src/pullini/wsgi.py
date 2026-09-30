"""WSGI entry point for Pullini (served by gunicorn in production)."""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pullini.settings")

application = get_wsgi_application()
