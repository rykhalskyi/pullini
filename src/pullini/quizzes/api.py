"""Authenticated quiz and page-read REST API (E6, T10/D-39…D-42).

Exposes the T9 quiz domain and the wiki source an agent needs to generate a
grounded quiz. Every resource is scoped to the token owner (D-32); plain Django
JSON views, no DRF (D-25).
"""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from pullini.accounts.auth import require_token
from pullini.api.http import ApiError, api_endpoint, isoformat, json_body
from pullini.artifacts.models import Artifact
from pullini.projects.access import visible_projects
from pullini.quizzes import services
from pullini.quizzes.models import Quiz
from pullini.wiki.models import Page

# A simple cap instead of pagination (out of scope for v1).
LIST_LIMIT = 200


def _quiz_queryset():
    return Quiz.objects.select_related("page", "page__project", "artifact").prefetch_related(
        "questions"
    )


def _get_owned_quiz(request: HttpRequest, pk: int) -> Quiz:
    return get_object_or_404(_quiz_queryset(), pk=pk, user=request.user)


def _target(quiz: Quiz) -> dict:
    if quiz.page_id:
        return {
            "project": quiz.page.project.slug,
            "path": quiz.page.path,
            "title": quiz.page.title,
        }
    return {"slug": quiz.artifact.slug, "title": quiz.artifact.title}


def serialize_quiz_list_item(quiz: Quiz) -> dict:
    return {
        "id": quiz.id,
        "target_type": quiz.target_type,
        "target": _target(quiz),
        "question_count": len(quiz.questions.all()),
        "stale": quiz.is_stale,
        "last_score": quiz.last_score,
        "best_score": quiz.best_score,
        "created_at": isoformat(quiz.created_at),
        "updated_at": isoformat(quiz.updated_at),
    }


def serialize_quiz_detail(quiz: Quiz) -> dict:
    data = serialize_quiz_list_item(quiz)
    data["questions"] = [
        {
            "position": question.position,
            "text": question.text,
            "options": question.options,
            "correct_index": question.correct_index,
            "explanation": question.explanation,
        }
        for question in quiz.questions.all()
    ]
    return data


def serialize_page_summary(page: Page) -> dict:
    return {
        "project": page.project.slug,
        "path": page.path,
        "title": page.title,
        "updated_at": isoformat(page.updated_at),
    }


def _resolve_target(request: HttpRequest, data: dict) -> dict:
    """Return the single ``{"page": Page}`` or ``{"artifact": Artifact}`` target."""
    has_page = "page" in data
    has_artifact = "artifact" in data
    if has_page == has_artifact:
        raise ApiError("invalid_field", 'Provide exactly one of "page" or "artifact".')

    if has_page:
        spec = data["page"]
        if not isinstance(spec, dict):
            raise ApiError("invalid_field", '"page" must be an object with "project" and "path".')
        project_slug = spec.get("project")
        path = spec.get("path")
        if not isinstance(project_slug, str) or not project_slug.strip():
            raise ApiError("invalid_field", '"page.project" must be a non-empty string.')
        if not isinstance(path, str) or not path.strip():
            raise ApiError("invalid_field", '"page.path" must be a non-empty string.')
        project = get_object_or_404(visible_projects(request.user), slug=project_slug)
        return {"page": get_object_or_404(Page, project=project, path=path)}

    slug = data["artifact"]
    if not isinstance(slug, str) or not slug.strip():
        raise ApiError("invalid_field", '"artifact" must be a non-empty slug.')
    return {"artifact": get_object_or_404(Artifact, user=request.user, slug=slug)}


@require_token
@api_endpoint
@require_http_methods(["GET", "POST"])
def quiz_collection(request: HttpRequest):
    if request.method == "GET":
        quizzes = services.list_quizzes(request.user)[:LIST_LIMIT]
        return JsonResponse({"quizzes": [serialize_quiz_list_item(quiz) for quiz in quizzes]})

    data = json_body(request)
    target = _resolve_target(request, data)
    existing = services.get_quiz(request.user, **target)
    try:
        quiz = services.create_quiz(request.user, questions=data.get("questions"), **target)
    except services.QuizError as exc:
        raise ApiError("invalid_field", str(exc)) from exc
    return JsonResponse(serialize_quiz_detail(quiz), status=200 if existing else 201)


@require_token
@api_endpoint
@require_http_methods(["GET", "DELETE"])
def quiz_item(request: HttpRequest, pk: int):
    quiz = _get_owned_quiz(request, pk)
    if request.method == "DELETE":
        quiz.delete()
        return HttpResponse(status=204)
    return JsonResponse(serialize_quiz_detail(quiz))


@require_token
@api_endpoint
@require_http_methods(["POST"])
def quiz_attempt(request: HttpRequest, pk: int):
    quiz = _get_owned_quiz(request, pk)
    data = json_body(request)
    answers = data.get("answers")
    if not isinstance(answers, list):
        raise ApiError("invalid_field", '"answers" must be a list.')
    try:
        result = services.score_submission(quiz, answers)
    except services.QuizError as exc:
        raise ApiError("invalid_field", str(exc)) from exc
    return JsonResponse(result)


@require_token
@api_endpoint
@require_http_methods(["GET"])
def page_collection(request: HttpRequest):
    """List wiki pages the token owner may read (D-42)."""
    pages = Page.objects.filter(project__in=visible_projects(request.user)).select_related(
        "project"
    )
    project_slug = request.GET.get("project", "").strip()
    if project_slug:
        pages = pages.filter(project__slug=project_slug)
    pages = pages.order_by("project__name", "path")[:LIST_LIMIT]
    return JsonResponse({"pages": [serialize_page_summary(page) for page in pages]})


@require_token
@api_endpoint
@require_http_methods(["GET"])
def page_item(request: HttpRequest, project: str, page_path: str):
    """Return the source Markdown of one wiki page (D-42)."""
    project_obj = get_object_or_404(visible_projects(request.user), slug=project)
    page = get_object_or_404(Page, project=project_obj, path=page_path)
    return JsonResponse(
        {
            "project": page.project.slug,
            "path": page.path,
            "title": page.title,
            "content": page.content,
            "updated_at": isoformat(page.updated_at),
        }
    )
