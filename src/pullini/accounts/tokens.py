"""Token generation, hashing and verification (E6, D-30).

Secret format: ``pln_<8 hex>_<43 urlsafe>``. The ``<8 hex>`` half is stored in
clear as ``prefix`` so lookups never scan every row; verification then compares
the SHA-256 of the full secret with the stored hash in constant time. No scopes:
a token carries its user's full artifact-API access (T3 spec).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from django.db import IntegrityError, transaction
from django.utils import timezone

from pullini.accounts.models import PersonalAccessToken

TOKEN_PREFIX = "pln_"
_PREFIX_BYTES = 4
_SECRET_BYTES = 32
_MAX_CREATE_ATTEMPTS = 5


def digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def extract_prefix(raw: str) -> str | None:
    """Return the public prefix embedded in a raw token, or ``None`` if malformed."""
    if not raw.startswith(TOKEN_PREFIX):
        return None
    prefix, sep, _ = raw[len(TOKEN_PREFIX) :].partition("_")
    if not sep or not prefix:
        return None
    return prefix


def create_for_user(user, name: str, *, expires_at=None) -> tuple[PersonalAccessToken, str]:
    """Create a token and return ``(token, raw_secret)``; the raw secret is not stored."""
    for _ in range(_MAX_CREATE_ATTEMPTS):
        prefix = secrets.token_hex(_PREFIX_BYTES)
        raw = f"{TOKEN_PREFIX}{prefix}_{secrets.token_urlsafe(_SECRET_BYTES)}"
        try:
            with transaction.atomic():
                token = PersonalAccessToken.objects.create(
                    user=user,
                    name=name,
                    prefix=prefix,
                    token_hash=digest(raw),
                    expires_at=expires_at,
                )
        except IntegrityError:
            continue
        return token, raw
    raise RuntimeError("Could not allocate a unique token prefix")


def authenticate(raw: str | None) -> PersonalAccessToken | None:
    """Resolve a raw bearer secret to a valid token, or ``None``."""
    if not raw:
        return None
    prefix = extract_prefix(raw)
    if prefix is None:
        return None
    token = PersonalAccessToken.objects.select_related("user").filter(prefix=prefix).first()
    if token is None:
        return None
    if not hmac.compare_digest(token.token_hash, digest(raw)):
        return None
    if not token.is_valid or not token.user.is_active:
        return None
    return token


def touch_last_used(token: PersonalAccessToken) -> None:
    now = timezone.now()
    PersonalAccessToken.objects.filter(pk=token.pk).update(last_used_at=now)
    token.last_used_at = now
