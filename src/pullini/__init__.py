"""Pullini - a read-only Git-backed wiki browser."""

from importlib.metadata import PackageNotFoundError, version

try:
    # The single source of truth is [project].version in pyproject.toml.
    __version__ = version("pullini")
except PackageNotFoundError:  # pragma: no cover - running from an uninstalled checkout
    __version__ = "0.0.0+unknown"
