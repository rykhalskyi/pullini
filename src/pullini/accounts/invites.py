"""One-time password setup links for newly created users.

The admin never chooses a password for another person. Instead, a signed token
is generated from the user's current (unusable) password hash, so setting a
password invalidates the link. ``set_unusable_password()`` changes the hash as
well, which is how resetting a password revokes every previously issued link.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

SETUP_LINKS_SESSION_KEY = "password_setup_urls"


class PasswordSetupTokenGenerator(PasswordResetTokenGenerator):
    """Namespace setup tokens away from Django's password-reset tokens.

    Unlike the built-in generator the email address is not part of the hash:
    the admin may fill in the user's email after generating the link without
    invalidating it.
    """

    key_salt = "pullini.accounts.invites.PasswordSetupTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        login_timestamp = (
            "" if user.last_login is None else user.last_login.replace(microsecond=0, tzinfo=None)
        )
        return f"{user.pk}{user.password}{login_timestamp}{timestamp}"


password_setup_token_generator = PasswordSetupTokenGenerator()


def build_password_setup_url(request, user) -> str:
    """Return an absolute one-time setup URL for ``user``."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = password_setup_token_generator.make_token(user)
    path = reverse("password_setup", kwargs={"uidb64": uidb64, "token": token})
    return request.build_absolute_uri(path)


def remember_setup_link(request, user, url: str) -> None:
    """Keep a setup URL until the matching user's change page is rendered."""
    links = request.session.get(SETUP_LINKS_SESSION_KEY, {})
    links[str(user.pk)] = url
    request.session[SETUP_LINKS_SESSION_KEY] = links


def pop_setup_link(request, user) -> str | None:
    """Return and forget the pending setup URL for ``user``, if any."""
    links = request.session.get(SETUP_LINKS_SESSION_KEY, {})
    url = links.pop(str(user.pk), None)
    if links:
        request.session[SETUP_LINKS_SESSION_KEY] = links
    else:
        request.session.pop(SETUP_LINKS_SESSION_KEY, None)
    return url


def format_setup_timeout(seconds: int) -> str:
    """Render a link timeout in the largest whole unit, e.g. ``2 hours``."""
    for unit_seconds, unit in ((86400, "day"), (3600, "hour"), (60, "minute")):
        if seconds >= unit_seconds and seconds % unit_seconds == 0:
            value = seconds // unit_seconds
            return f"{value} {unit}{'' if value == 1 else 's'}"
    return f"{seconds} second{'' if seconds == 1 else 's'}"


def user_from_uidb64(uidb64: str):
    """Resolve the ``uidb64`` URL segment to a user, or ``None`` if malformed."""
    try:
        pk = force_str(urlsafe_base64_decode(uidb64))
        return get_user_model().objects.filter(pk=pk).first()
    except TypeError, ValueError, OverflowError, UnicodeDecodeError:
        return None


def is_valid_setup_token(user, token: str) -> bool:
    """A setup link is valid only for an active user who cannot log in yet."""
    if user is None or not user.is_active or user.has_usable_password():
        return False
    return password_setup_token_generator.check_token(user, token)
