"""Quiz tests: models, services and the web surface (E6, T9/D-39…D-41)."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse

from pullini.artifacts import services as artifact_services
from pullini.projects.models import Project
from pullini.quizzes import services
from pullini.quizzes.models import Quiz
from pullini.wiki.models import Page

pytestmark = pytest.mark.django_db


def make_user(username: str = "reader"):
    return get_user_model().objects.create_user(username=username, password="s3cret-pass")


def make_project(name: str = "Payments", *, enabled: bool = True) -> Project:
    return Project.objects.create(
        name=name,
        repo_url="https://git.example.com/payments.git",
        enabled=enabled,
    )


def make_page(project: Project, path: str = "guide/setup.md", **kwargs) -> Page:
    defaults = {
        "url_path": path.rsplit(".", 1)[0],
        "title": path,
        "content": "# Page",
        "html": "<h1>Page</h1>",
        "plain_text": "Page",
        "content_hash": f"hash-{path}",
    }
    defaults.update(kwargs)
    return Page.objects.create(project=project, path=path, **defaults)


def make_artifact(user, title: str = "Report"):
    return artifact_services.create_artifact(user, title=title, content="# A")


def q(text: str = "Q", options=("a", "b"), correct: int = 0, explanation: str = ""):
    return {
        "text": text,
        "options": list(options),
        "correct_index": correct,
        "explanation": explanation,
    }


# --- models & creation --------------------------------------------------------


def test_create_quiz_creates_ordered_questions():
    user = make_user()
    page = make_page(make_project())

    quiz = services.create_quiz(user, page=page, questions=[q("First"), q("Second", correct=1)])

    assert quiz.user == user
    assert quiz.target_type == "page"
    assert quiz.source_hash == page.content_hash
    assert [question.text for question in quiz.questions.all()] == ["First", "Second"]
    assert [question.position for question in quiz.questions.all()] == [0, 1]
    assert quiz.last_score is None
    assert quiz.best_score is None


def test_quiz_is_unique_per_user_and_page():
    user = make_user()
    page = make_page(make_project())
    services.create_quiz(user, page=page, questions=[q()])

    with pytest.raises(IntegrityError), transaction.atomic():
        Quiz.objects.create(user=user, page=page, target_type="page", source_hash="x")


def test_quiz_requires_exactly_one_target():
    user = make_user()
    page = make_page(make_project())
    artifact = make_artifact(user)

    with pytest.raises(IntegrityError), transaction.atomic():
        Quiz.objects.create(
            user=user, page=page, artifact=artifact, target_type="page", source_hash="x"
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        Quiz.objects.create(user=user, target_type="page", source_hash="x")


def test_create_quiz_replaces_the_existing_one():
    user = make_user()
    page = make_page(make_project())
    first = services.create_quiz(user, page=page, questions=[q("Old"), q("Also old")])

    second = services.create_quiz(user, page=page, questions=[q("New")])

    assert second.pk == first.pk
    assert Quiz.objects.filter(user=user, page=page).count() == 1
    assert [question.text for question in second.questions.all()] == ["New"]


def test_create_quiz_for_an_artifact():
    user = make_user()
    artifact = make_artifact(user)

    quiz = services.create_quiz(user, artifact=artifact, questions=[q()])

    assert quiz.target_type == "artifact"
    assert quiz.target == artifact
    assert quiz.source_hash == artifact.content_hash


def test_quizzes_are_scoped_per_user():
    page = make_page(make_project())
    owner = make_user("owner")
    other = make_user("other")

    services.create_quiz(owner, page=page, questions=[q()])
    services.create_quiz(other, page=page, questions=[q("Other")])

    assert Quiz.objects.filter(page=page).count() == 2
    assert services.get_quiz(owner, page=page).questions.count() == 1


def test_cascade_deletes_quiz_with_its_source():
    user = make_user()
    page = make_page(make_project())
    artifact = make_artifact(user)
    services.create_quiz(user, page=page, questions=[q()])
    services.create_quiz(user, artifact=artifact, questions=[q()])

    page.delete()
    artifact.delete()

    assert Quiz.objects.count() == 0


def test_is_stale_tracks_the_source_hash():
    user = make_user()
    page = make_page(make_project())
    quiz = services.create_quiz(user, page=page, questions=[q()])
    assert quiz.is_stale is False

    page.content_hash = "changed"
    page.save(update_fields=["content_hash"])

    assert services.get_quiz(user, page=page).is_stale is True


# --- validation ---------------------------------------------------------------


def test_create_quiz_requires_exactly_one_target():
    user = make_user()
    page = make_page(make_project())
    artifact = make_artifact(user)

    with pytest.raises(services.QuizError):
        services.create_quiz(user, questions=[q()])
    with pytest.raises(services.QuizError):
        services.create_quiz(user, page=page, artifact=artifact, questions=[q()])


@pytest.mark.parametrize(
    "questions",
    [
        [],
        [q()] * (services.MAX_QUESTIONS + 1),
        [{"text": "Q", "options": ["only-one"], "correct_index": 0}],
        [{"text": "", "options": ["a", "b"], "correct_index": 0}],
        [{"text": "Q", "options": ["a", "b"], "correct_index": 2}],
        [{"text": "Q", "options": ["a", "b"]}],
    ],
)
def test_invalid_questions_are_rejected(questions):
    user = make_user()
    page = make_page(make_project())

    with pytest.raises(services.QuizError):
        services.create_quiz(user, page=page, questions=questions)

    assert Quiz.objects.count() == 0


# --- scoring ------------------------------------------------------------------


def test_score_submission_updates_last_and_best():
    user = make_user()
    page = make_page(make_project())
    quiz = services.create_quiz(
        user,
        page=page,
        questions=[q(correct=1), q(correct=0), q(correct=2, options=("a", "b", "c"))],
    )

    perfect = services.score_submission(quiz, [1, 0, 2])
    assert perfect["score"] == 3
    assert perfect["total"] == 3
    assert quiz.best_score == 3

    partial = services.score_submission(quiz, [0, 0, 2])
    assert partial["score"] == 2
    assert partial["last_score"] == 2
    assert partial["best_score"] == 3


def test_score_submission_accepts_strings_and_missing_answers():
    user = make_user()
    page = make_page(make_project())
    quiz = services.create_quiz(user, page=page, questions=[q(correct=1), q(correct=0)])

    result = services.score_submission(quiz, ["1"])

    assert result["score"] == 1
    assert result["results"][1]["given"] is None
    assert result["results"][1]["is_correct"] is False


# --- web ----------------------------------------------------------------------


def test_quiz_views_require_login(client):
    user = make_user()
    quiz = services.create_quiz(user, page=make_page(make_project()), questions=[q()])

    detail = client.get(reverse("quizzes:detail", args=[quiz.pk]))
    submit = client.post(reverse("quizzes:submit", args=[quiz.pk]))

    assert detail.status_code == 302
    assert detail.url.startswith("/login/")
    assert submit.status_code == 302
    assert submit.url.startswith("/login/")


def test_quiz_submit_rejects_get(client):
    user = make_user()
    client.force_login(user)
    quiz = services.create_quiz(user, page=make_page(make_project()), questions=[q()])

    assert client.get(reverse("quizzes:submit", args=[quiz.pk])).status_code == 405


def test_quiz_is_owner_scoped(client):
    owner = make_user("owner")
    other = make_user("other")
    quiz = services.create_quiz(owner, page=make_page(make_project()), questions=[q()])
    client.force_login(other)

    response = client.get(reverse("quizzes:detail", args=[quiz.pk]))

    assert response.status_code == 404


def test_quiz_detail_shows_questions(client):
    user = make_user()
    client.force_login(user)
    quiz = services.create_quiz(
        user, page=make_page(make_project()), questions=[q("What is 2+2?", options=("3", "4"))]
    )

    content = client.get(reverse("quizzes:detail", args=[quiz.pk])).content

    assert b"What is 2+2?" in content
    assert b"4" in content


def test_quiz_submit_scores_and_renders(client):
    user = make_user()
    client.force_login(user)
    quiz = services.create_quiz(
        user,
        page=make_page(make_project()),
        questions=[q(correct=1, options=("wrong", "right")), q(correct=0)],
    )

    response = client.post(
        reverse("quizzes:submit", args=[quiz.pk]),
        {"answer-0": "1", "answer-1": "0"},
    )

    assert response.status_code == 200
    assert b"2/2" in response.content
    quiz.refresh_from_db()
    assert quiz.last_score == 2
    assert quiz.best_score == 2


def test_quiz_submit_shows_back_to_article(client):
    user = make_user()
    client.force_login(user)
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    quiz = services.create_quiz(user, page=page, questions=[q(correct=0)])

    response = client.post(
        reverse("quizzes:submit", args=[quiz.pk]),
        {"answer-0": "0"},
    )

    assert response.status_code == 200
    assert b"Back to article" in response.content
    assert reverse("wiki:page", args=[project.slug, page.url_path]).encode() in response.content


def test_wiki_page_shows_quiz_button_and_score(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    quiz = services.create_quiz(user, page=page, questions=[q(correct=0)])
    services.score_submission(quiz, [0])
    client.force_login(user)

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert reverse("quizzes:detail", args=[quiz.pk]).encode() in content
    assert b"1/1" in content


def test_wiki_page_shows_no_quiz_hint(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    client.force_login(user)

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert b"No quiz yet" in content
    assert b"Create a quiz" in content
    assert f"{project.slug}/{page.path}".encode() in content


def test_artifact_detail_no_quiz_hint_copies_slug(client):
    user = make_user()
    artifact = make_artifact(user)
    client.force_login(user)

    content = client.get(reverse("artifacts:detail", args=[artifact.slug])).content

    assert b"Create a quiz" in content
    assert b"data-quiz-ref" in content
    assert b"data-copy-quiz-ref" in content


def test_project_detail_lists_page_quizzes(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    services.create_quiz(user, page=page, questions=[q()])
    client.force_login(user)

    content = client.get(reverse("projects:detail", args=[project.slug])).content

    assert b"Quizzes" in content
    assert b"Home" in content


def test_artifact_detail_shows_quiz_button(client):
    user = make_user()
    artifact = make_artifact(user)
    quiz = services.create_quiz(user, artifact=artifact, questions=[q()])
    client.force_login(user)

    content = client.get(reverse("artifacts:detail", args=[artifact.slug])).content

    assert reverse("quizzes:detail", args=[quiz.pk]).encode() in content


def test_anonymous_wiki_page_shows_no_quiz_affordance(client):
    user = make_user()
    project = make_project()
    page = make_page(project, path="index.md", title="Home")
    services.create_quiz(user, page=page, questions=[q()])

    content = client.get(reverse("wiki:page", args=[project.slug, page.url_path])).content

    assert b"No quiz yet" not in content
