"""Q&A web view: the read-only static FAQ for a page or artifact (E6, T12).

Q&A sets are private: the view is login-gated and scoped to the owner. Content is
agent-authored through the API/MCP; this surface only lets the owner read it
(D-44).
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from pullini.qanda.models import QandA


@login_required
def qanda_detail(request: HttpRequest, pk: int) -> HttpResponse:
    qanda = get_object_or_404(
        QandA.objects.select_related("page", "page__project", "artifact").prefetch_related("items"),
        pk=pk,
        user=request.user,
    )
    return render(request, "qanda/detail.html", {"qanda": qanda})
