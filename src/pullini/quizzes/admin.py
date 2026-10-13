"""Django admin registration for quizzes.

Quizzes are authored through the API/MCP (D-39), so this is a diagnostics
surface over the stored questions and scores.
"""

from __future__ import annotations

from django.contrib import admin

from pullini.quizzes.models import Question, Quiz


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    readonly_fields = ("position", "text", "options", "correct_index", "explanation")


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("user", "target_type", "title", "question_count", "last_score", "best_score")
    list_filter = ("target_type", "updated_at")
    search_fields = ("user__username", "page__path", "artifact__slug")
    readonly_fields = ("source_hash", "last_score", "best_score", "created_at", "updated_at")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "position", "text")
    search_fields = ("text",)
