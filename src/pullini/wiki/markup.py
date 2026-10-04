"""Markdown rendering helpers (HLD §8).

Pullini generates the presentation, never the content: the source Markdown
stays authoritative and is only ever read.
"""

from __future__ import annotations

import hashlib
import posixpath
import re

import markdown as markdown_lib
import nh3
from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor

MERMAID_CLASS = "mermaid"


class _MermaidPostprocessor(Postprocessor):
    """Turn mermaid fenced blocks into ``<div class="mermaid">`` containers.

    Run as a postprocessor because ``fenced_code`` stashes its HTML in
    ``htmlStash``; the real ``<pre><code>`` only appears after serialization.
    The diagram source stays as escaped text and is rendered client-side.
    Mermaid ``%%{ ... }%%`` directives are dropped: they can override the
    security level that the front-end initializer sets. Directives may span
    multiple lines, so they are matched as a block rather than per line.
    """

    _BLOCK_RE = re.compile(
        r'<pre[^>]*><code class="[^"]*\blanguage-mermaid\b[^"]*"[^>]*>(.*?)</code></pre>',
        re.DOTALL | re.IGNORECASE,
    )
    _DIRECTIVE_RE = re.compile(r"%%\{.*?\}%%", re.DOTALL)

    def run(self, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            source = self._DIRECTIVE_RE.sub("", match.group(1)).strip()
            return f'<div class="{MERMAID_CLASS}">{source}</div>'

        return self._BLOCK_RE.sub(replace, text)


class _MermaidExtension(Extension):
    def extendMarkdown(self, md) -> None:  # noqa: N802 - markdown API name
        md.postprocessors.register(_MermaidPostprocessor(md), "mermaid", 10)


MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "tables",
    "attr_list",
    "sane_lists",
    "toc",
    _MermaidExtension(),
]
MARKDOWN_SUFFIXES = (".md", ".markdown")

# Rendered Markdown is untrusted: it comes from third-party Git repositories.
# Raw HTML and event handlers are stripped, and only these tags/attributes
# survive sanitization.
ALLOWED_TAGS = {
    "a",
    "abbr",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "kbd",
    "li",
    "ol",
    "p",
    "pre",
    "s",
    "span",
    "strong",
    "sub",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}
ALLOWED_ATTRIBUTES = {
    "*": {"class", "id"},
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "th": {"align", "colspan", "rowspan"},
    "td": {"align", "colspan", "rowspan"},
}
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

_TAG_RE = re.compile(r"<[^>]+>")
_HREF_RE = re.compile(r'href="([^"]+)"')
_SRC_RE = re.compile(r'src="([^"]+)"')


def sanitize(html: str) -> str:
    """Strip scripts, event handlers and dangerous URL schemes from rendered HTML."""
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer",
    )


def render(content: str) -> str:
    return sanitize(markdown_lib.markdown(content, extensions=MARKDOWN_EXTENSIONS))


def has_mermaid(html: str) -> bool:
    """True when rendered HTML contains a Mermaid container to initialize."""
    return f'class="{MERMAID_CLASS}"' in html


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
