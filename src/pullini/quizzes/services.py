"""Quiz services: question validation, upsert and scoring (E6, T9/D-39…D-41).

Questions are authored by an agent and submitted as plain data; everything is
validated here so the API, MCP and web layers share one set of rules. The rendered
score never leaves the server's control (D-40).
"""

from __future__ import annotations

from django.db import transaction

from pullini.quizzes.models import Question, Quiz, TargetType

MAX_QUESTIONS = 10
MIN_OPTIONS = 2
MAX_OPTIONS = 6
MAX_QUESTION_TEXT = 500
MAX_OPTION_TEXT = 300
MAX_EXPLANATION = 1000


class QuizError(ValueError):
    """A quiz payload supplied by the caller is not acceptable."""


def _clean_text(value, *, field: str, max_len: int, required: bool = True) -> str:
    text = " ".join(str(value).split()) if value is not None else ""
    if not text:
        if required:
            raise QuizError(f"Question {field} must not be empty.")
        return ""
    if len(text) > max_len:
        raise QuizError(f"Question {field} must be at most {max_len} characters.")
    return text


def _as_int(value) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def validate_questions(questions) -> list[dict]:
    """Normalize and validate an ordered list of question payloads.

    Pure: it never touches the database, so callers can reject bad input before
    mutating anything. Each question is a mapping with ``text``, ``options``,
    ``correct_index`` and an optional ``explanation``.
    """
    if not isinstance(questions, (list, tuple)):
        raise QuizError('"questions" must be a list.')
    if not questions:
        raise QuizError("A quiz needs at least one question.")
    if len(questions) > MAX_QUESTIONS:
        raise QuizError(f"A quiz can have at most {MAX_QUESTIONS} questions.")

    cleaned: list[dict] = []
    for raw in questions:
        if not isinstance(raw, dict):
            raise QuizError("Each question must be an object.")
        text = _clean_text(raw.get("text"), field="text", max_len=MAX_QUESTION_TEXT)

        options_raw = raw.get("options")
        if not isinstance(options_raw, (list, tuple)):
            raise QuizError("Each question needs an options list.")
        options = [
            _clean_text(option, field="option", max_len=MAX_OPTION_TEXT) for option in options_raw
        ]
        if len(options) < MIN_OPTIONS:
            raise QuizError(f"Each question needs at least {MIN_OPTIONS} options.")
        if len(options) > MAX_OPTIONS:
            raise QuizError(f"Each question can have at most {MAX_OPTIONS} options.")

        correct_index = _as_int(raw.get("correct_index"))
        if correct_index is None or correct_index < 0 or correct_index >= len(options):
            raise QuizError('"correct_index" must point at one of the options.')

        explanation = _clean_text(
            raw.get("explanation", ""),
            field="explanation",
            max_len=MAX_EXPLANATION,
            required=False,
        )
        cleaned.append(
            {
                "text": text,
                "options": options,
                "correct_index": correct_index,
                "explanation": explanation,
            }
        )
    return cleaned


def _resolve_target(page=None, artifact=None):
    if (page is None) == (artifact is None):
        raise QuizError("A quiz needs exactly one target: a page or an artifact.")
    return (TargetType.PAGE if page is not None else TargetType.ARTIFACT), (page or artifact)


def create_quiz(user, *, page=None, artifact=None, questions) -> Quiz:
    """Create or replace the owner's quiz for one page or artifact (D-39)."""
    target_type, target = _resolve_target(page=page, artifact=artifact)
    cleaned = validate_questions(questions)

    with transaction.atomic():
        quiz, _ = Quiz.objects.update_or_create(
            user=user,
            page=page,
            artifact=artifact,
            defaults={"target_type": target_type, "source_hash": target.content_hash},
        )
        quiz.questions.all().delete()
        Question.objects.bulk_create(
            Question(quiz=quiz, position=position, **question)
            for position, question in enumerate(cleaned)
        )
    return quiz


def get_quiz(user, *, page=None, artifact=None) -> Quiz | None:
    """The owner's quiz for a target, or ``None``."""
    if (page is None) == (artifact is None):
        return None
    return Quiz.objects.filter(user=user, page=page, artifact=artifact).first()


def list_quizzes(user):
    """All of the owner's quizzes, most recently updated first."""
    return (
        Quiz.objects.filter(user=user)
        .select_related("page", "page__project", "artifact")
        .prefetch_related("questions")
    )


def quizzes_for_project(user, project):
    """The owner's page quizzes for one project."""
    if not getattr(user, "is_authenticated", False):
        return Quiz.objects.none()
    return (
        Quiz.objects.filter(user=user, page__project=project)
        .select_related("page")
        .prefetch_related("questions")
    )


def delete_quiz(quiz: Quiz) -> None:
    """Remove a quiz and its questions."""
    quiz.delete()


def score_submission(quiz: Quiz, answers) -> dict:
    """Score ``answers`` against the quiz and update last/best score (D-40)."""
    if not isinstance(answers, (list, tuple)):
        raise QuizError('"answers" must be a list.')

    questions = list(quiz.questions.all())
    results: list[dict] = []
    correct_count = 0
    for index, question in enumerate(questions):
        answer = _as_int(answers[index]) if index < len(answers) else None
        is_correct = answer == question.correct_index
        correct_count += int(is_correct)
        results.append(
            {
                "given": answer,
                "correct_index": question.correct_index,
                "is_correct": is_correct,
            }
        )

    quiz.last_score = correct_count
    if quiz.best_score is None or correct_count > quiz.best_score:
        quiz.best_score = correct_count
    quiz.save(update_fields=["last_score", "best_score", "updated_at"])

    return {
        "score": correct_count,
        "total": len(questions),
        "last_score": quiz.last_score,
        "best_score": quiz.best_score,
        "results": results,
    }
