"""Django admin registration for Q&A sets.

Q&A sets are authored through the API/MCP (D-43), so this is a diagnostics
surface over the stored items.
"""

from __future__ import annotations

from django.contrib import admin

from pullini.qanda.models import QandA, QandAItem


class QandAItemInline(admin.TabularInline):
    model = QandAItem
    extra = 0
    readonly_fields = ("position", "question", "answer", "answer_html")


@admin.register(QandA)
class QandAAdmin(admin.ModelAdmin):
    list_display = ("user", "target_type", "title", "item_count", "updated_at")
    list_filter = ("target_type", "updated_at")
    search_fields = ("user__username", "page__path", "artifact__slug")
    readonly_fields = ("source_hash", "created_at", "updated_at")
    inlines = [QandAItemInline]


@admin.register(QandAItem)
class QandAItemAdmin(admin.ModelAdmin):
    list_display = ("qanda", "position", "question")
    search_fields = ("question",)
