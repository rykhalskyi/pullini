"""Project visibility policy shared by views and services (T15, HLD §4).

Projects are owner-private: only the owner and superusers may browse a project
and its wiki pages. Everyone else, including anonymous visitors, gets a 404.
"""

from __future__ import annotations

from pullini.projects.models import Project


def visible_projects(user):
    """Projects the given user may browse.

    Superusers see every project (including disabled ones) for oversight;
    authenticated users see their own; anonymous visitors see none.
    """
    if user is None or not user.is_authenticated:
        return Project.objects.none()
    if user.is_superuser:
        return Project.objects.all()
    return Project.objects.filter(user=user)


def is_owner(user, project: Project) -> bool:
    """Whether ``user`` owns ``project`` and may manage it from the web UI.

    Superusers manage projects exclusively through the Django admin, so this is
    strictly the owner (T15).
    """
    if user is None or not user.is_authenticated:
        return False
    return project.user_id == user.id
