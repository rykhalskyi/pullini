"""Q&A services: entry validation and upsert (E6, T12/D-43…D-45).

Entries are authored by an agent and submitted as plain data; everything is
validated here so the API, MCP and web layers share one set of rules. Answers are
Markdown, rendered and sanitized **at write time** through the wiki markup pipeline
(D-44).
"""

from __future__ import annotations

from django.db import transaction

from pullini.qanda.models import QandA, QandAItem, TargetType
from pullini.wiki import markup

MAX_ENTRIES = 50
MAX_QUESTION_TEXT = 500
MAX_ANSWER_TEXT = 5000


class QandAError(ValueError):
    """A Q&A payload supplied by the caller is not acceptable."""


def _clean_question(value) -> str:
    text = " ".join(str(value).split()) if value is not None else ""
    if not text:
        raise QandAError("Question must not be empty.")
    if len(text) > MAX_QUESTION_TEXT:
        raise QandAError(f"Question must be at most {MAX_QUESTION_TEXT} characters.")
    return text


def _clean_answer(value) -> str:
    text = "" if value is None else str(value)
    if not text.strip():
        raise QandAError("Answer must not be empty.")
    if len(text) > MAX_ANSWER_TEXT:
        raise QandAError(f"Answer must be at most {MAX_ANSWER_TEXT} characters.")
    return text


def validate_entries(entries) -> list[dict]:
    """Normalize and validate an ordered list of question/answer payloads.

    Pure: it never touches the database, so callers can reject bad input before
    mutating anything. Each entry is a mapping with a ``question`` and an
    ``answer`` (Markdown); the rendered/sanitized ``answer_html`` is derived here.
    """
    if not isinstance(entries, (list, tuple)):
        raise QandAError('"entries" must be a list.')
    if not entries:
        raise QandAError("A Q&A set needs at least one entry.")
    if len(entries) > MAX_ENTRIES:
        raise QandAError(f"A Q&A set can have at most {MAX_ENTRIES} entries.")

    cleaned: list[dict] = []
    for raw in entries:
        if not isinstance(raw, dict):
            raise QandAError("Each entry must be an object.")
        question = _clean_question(raw.get("question"))
        answer = _clean_answer(raw.get("answer"))
        cleaned.append(
            {"question": question, "answer": answer, "answer_html": markup.render(answer)}
        )
    return cleaned


def _resolve_target(page=None, artifact=None):
    if (page is None) == (artifact is None):
        raise QandAError("A Q&A set needs exactly one target: a page or an artifact.")
    return (TargetType.PAGE if page is not None else TargetType.ARTIFACT), (page or artifact)


def create_qanda(user, *, page=None, artifact=None, entries) -> QandA:
    """Create or replace the owner's Q&A set for one page or artifact (D-43)."""
    target_type, target = _resolve_target(page=page, artifact=artifact)
    cleaned = validate_entries(entries)

    with transaction.atomic():
        qanda, _ = QandA.objects.update_or_create(
            user=user,
            page=page,
            artifact=artifact,
            defaults={"target_type": target_type, "source_hash": target.content_hash},
        )
        qanda.items.all().delete()
        QandAItem.objects.bulk_create(
            QandAItem(qanda=qanda, position=position, **entry)
            for position, entry in enumerate(cleaned)
        )
    return qanda


def get_qanda(user, *, page=None, artifact=None) -> QandA | None:
    """The owner's Q&A set for a target, or ``None``."""
    if (page is None) == (artifact is None):
        return None
    return QandA.objects.filter(user=user, page=page, artifact=artifact).first()


def list_qanda(user):
    """All of the owner's Q&A sets, most recently updated first."""
    return (
        QandA.objects.filter(user=user)
        .select_related("page", "page__project", "artifact")
        .prefetch_related("items")
    )


def qanda_for_project(user, project):
    """The owner's page Q&A sets for one project."""
    if not getattr(user, "is_authenticated", False):
        return QandA.objects.none()
    return (
        QandA.objects.filter(user=user, page__project=project)
        .select_related("page")
        .prefetch_related("items")
    )


def delete_qanda(qanda: QandA) -> None:
    """Remove a Q&A set and its items."""
    qanda.delete()
