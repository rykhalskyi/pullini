"""Markdown rendering helpers (HLD §8).

Pullini generates the presentation, never the content: the source Markdown
stays authoritative and is only ever read.
"""

from __future__ import annotations

import hashlib
import posixpath
import re

import markdown as markdown_lib

MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "attr_list", "sane_lists", "toc"]
MARKDOWN_SUFFIXES = (".md", ".markdown")

_TAG_RE = re.compile(r"<[^>]+>")
_HREF_RE = re.compile(r'href="([^"]+)"')
_SRC_RE = re.compile(r'src="([^"]+)"')


def render(content: str) -> str:
    return markdown_lib.markdown(content, extensions=MARKDOWN_EXTENSIONS)


def to_plain_text(html: str) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", html)).strip()


def extract_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            if title:
                return title
    return fallback


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def url_path_for(path: str) -> str:
    for suffix in MARKDOWN_SUFFIXES:
        if path.lower().endswith(suffix):
            return path[: -len(suffix)]
    return path


def _is_external(url: str) -> bool:
    return url.startswith(("http://", "https://", "//", "/", "#", "mailto:", "data:"))


def rewrite_urls(html: str, project_slug: str, page_dir: str) -> str:
    """Point relative links/uploads at Pullini's own page and asset routes."""
    page_dir = page_dir.strip("/")

    def resolve(url: str) -> str | None:
        joined = posixpath.join(page_dir, url) if page_dir and page_dir != "." else url
        resolved = posixpath.normpath(joined)
        if resolved.startswith(".."):
            return None
        return resolved

    def href_replacement(match: re.Match[str]) -> str:
        url = match.group(1)
        if _is_external(url):
            return match.group(0)
        path, _, anchor = url.partition("#")
        resolved = resolve(path)
        if resolved is None:
            return match.group(0)
        if path.lower().endswith(MARKDOWN_SUFFIXES):
            target = f"/projects/{project_slug}/wiki/{url_path_for(resolved)}/"
        else:
            target = f"/projects/{project_slug}/wiki/assets/{resolved}"
        if anchor:
            target = f"{target}#{anchor}"
        return f'href="{target}"'

    def src_replacement(match: re.Match[str]) -> str:
        url = match.group(1)
        if _is_external(url):
            return match.group(0)
        resolved = resolve(url)
        if resolved is None:
            return match.group(0)
        return f'src="/projects/{project_slug}/wiki/assets/{resolved}"'

    html = _HREF_RE.sub(href_replacement, html)
    return _SRC_RE.sub(src_replacement, html)
