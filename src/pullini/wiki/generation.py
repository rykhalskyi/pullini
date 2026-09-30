"""Generate read-only wiki pages from a project's cloned docs folder (HLD §8).

Regeneration is idempotent: pages whose content hash is unchanged are left
alone (so ``updated_at`` reflects real content changes), and pages whose source
files disappeared are removed.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from django.db import transaction

from pullini.projects.sync import repository_path
from pullini.wiki import markup
from pullini.wiki.models import Page


def docs_path(project) -> Path:
    return repository_path(project) / project.docs_folder.strip("/")


def _iter_markdown_files(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*")):
        if (
            path.is_file()
            and path.suffix.lower() in markup.MARKDOWN_SUFFIXES
            and ".git" not in path.parts
        ):
            yield path


def generate_pages(project) -> int:
    """Rebuild the project's pages from disk; return how many changed."""
    root = docs_path(project)
    seen: set[str] = set()
    changed = 0

    with transaction.atomic():
        if root.is_dir():
            for file_path in _iter_markdown_files(root):
                rel = file_path.relative_to(root).as_posix()
                seen.add(rel)

                content = file_path.read_text(encoding="utf-8", errors="replace")
                digest = markup.content_hash(content)
                existing = Page.objects.filter(project=project, path=rel).first()
                if existing and existing.content_hash == digest:
                    continue

                page_dir = str(Path(rel).parent)
                html = markup.rewrite_urls(markup.render(content), project.slug, page_dir)
                Page.objects.update_or_create(
                    project=project,
                    path=rel,
                    defaults={
                        "url_path": markup.url_path_for(rel),
                        "title": markup.extract_title(content, Path(rel).stem),
                        "content": content,
                        "html": html,
                        "plain_text": markup.to_plain_text(html),
                        "content_hash": digest,
                    },
                )
                changed += 1

        Page.objects.filter(project=project).exclude(path__in=seen).delete()

    return changed
