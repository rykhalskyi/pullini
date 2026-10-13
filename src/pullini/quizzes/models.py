"""User-owned quizzes about a wiki page or an artifact (E6, T9/D-39…D-41).

A quiz is private to its owner and targets **exactly one** source: a Git-derived
:class:`~pullini.wiki.models.Page` or a user-owned
:class:`~pullini.artifacts.models.Artifact`. There is one quiz per (user, target);
regenerating replaces it (upsert, D-39). The source's ``content_hash`` is captured
at generation so the UI can flag a quiz that has gone stale after a re-sync
(D-41). Questions are agent-authored through the API/MCP; the quiz row simply
records the owner's last and best score (self-study, D-40).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse


class TargetType(models.TextChoices):
    PAGE = "page", "Page"
    ARTIFACT = "artifact", "Artifact"


class Quiz(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    # Exactly one of these is set; both cascade from their source (D-39).
    page = models.ForeignKey(
        "wiki.Page",
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True,
        blank=True,
    )
    artifact = models.ForeignKey(
        "artifacts.Artifact",
        on_delete=models.CASCADE,
        related_name="quizzes",
        null=True,
        blank=True,
    )
    target_type = models.CharField(max_length=20, choices=TargetType.choices)

    # The source page's content hash at generation (D-41).
    source_hash = models.CharField(max_length=64)

    last_score = models.PositiveSmallIntegerField(null=True, blank=True)
    best_score = models.PositiveSmallIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "page"],
                name="unique_quiz_per_user_page",
            ),
            models.UniqueConstraint(
                fields=["user", "artifact"],
                name="unique_quiz_per_user_artifact",
            ),
            models.CheckConstraint(
                condition=(
                    Q(page__isnull=False, artifact__isnull=True)
                    | Q(page__isnull=True, artifact__isnull=False)
                ),
                name="quiz_exactly_one_target",
            ),
        ]
        indexes = [models.Index(fields=["user", "-updated_at"])]

    def __str__(self) -> str:
        return f"{self.user}:{self.target_type}"

    def get_absolute_url(self) -> str:
        return reverse("quizzes:detail", kwargs={"pk": self.pk})

    @property
    def target(self):
        """The single source this quiz is about."""
        return self.page if self.page_id else self.artifact

    @property
    def title(self) -> str:
        return self.target.title

    @property
    def source_url(self) -> str:
        if self.page_id:
            return reverse(
                "wiki:page",
                kwargs={"slug": self.page.project.slug, "page_path": self.page.url_path},
            )
        return reverse("artifacts:detail", kwargs={"slug": self.artifact.slug})

    @property
    def question_count(self) -> int:
        return self.questions.count()

    @property
    def is_stale(self) -> bool:
        """True when the source changed since the quiz was generated (D-41)."""
        target = self.target
        return target is not None and self.source_hash != target.content_hash


class Question(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    position = models.PositiveIntegerField()
    text = models.TextField()
    # A JSON list of option strings; ``correct_index`` points into it.
    options = models.JSONField(default=list)
    correct_index = models.PositiveSmallIntegerField()
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["quiz", "position"],
                name="unique_question_position_per_quiz",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.quiz_id}#{self.position}"
