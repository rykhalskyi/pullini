"""Project visibility policy shared by views and services (T15, HLD §4).

Projects are owner-private: only the owner and superusers may browse a project
and its wiki pages. Everyone else, including anonymous visitors, gets a 404.
"""

from __future__ import annotations

from pullini.projects.models import Project


def visible_projects(user):
    """Projects the given user may browse.

    Superusers see every project (including disabled ones); authenticated users
    see their own; anonymous visitors see none.
    """
    if user is None or not user.is_authenticated:
        return Project.objects.none()
    if user.is_superuser:
        return Project.objects.all()
    return Project.objects.filter(user=user)


def can_manage(user, project: Project) -> bool:
    """Whether ``user`` may refresh or delete ``project`` (owner or superuser)."""
    if user is None or not user.is_authenticated:
        return False
    return user.is_superuser or project.user_id == user.id
