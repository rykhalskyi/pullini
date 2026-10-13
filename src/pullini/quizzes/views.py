"""Quiz web views: taking a quiz and submitting answers (E6, T9).

Quizzes are private: every view is login-gated and scoped to the owner. Content
is agent-authored through the API/MCP; this surface only lets the owner answer
and see a score (D-40).
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from pullini.quizzes import services
from pullini.quizzes.models import Quiz


def _get_quiz(request: HttpRequest, pk: int) -> Quiz:
    return get_object_or_404(
        Quiz.objects.select_related("page", "page__project", "artifact"),
        pk=pk,
        user=request.user,
    )


def _render(request: HttpRequest, quiz: Quiz, result: dict | None = None) -> HttpResponse:
    questions = list(quiz.questions.all())
    if result is not None:
        rows = [
            {"question": question, "result": answer}
            for question, answer in zip(questions, result["results"], strict=True)
        ]
    else:
        rows = [{"question": question, "result": None} for question in questions]
    return render(request, "quizzes/detail.html", {"quiz": quiz, "rows": rows, "result": result})


@login_required
def quiz_detail(request: HttpRequest, pk: int) -> HttpResponse:
    quiz = _get_quiz(request, pk)
    return _render(request, quiz)


@login_required
@require_POST
def quiz_submit(request: HttpRequest, pk: int) -> HttpResponse:
    quiz = _get_quiz(request, pk)
    questions = list(quiz.questions.all())
    answers = [request.POST.get(f"answer-{question.position}") for question in questions]
    try:
        result = services.score_submission(quiz, answers)
    except services.QuizError as exc:
        messages.error(request, str(exc))
        result = None
    return _render(request, quiz, result=result)
