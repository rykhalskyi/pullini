"""Personal access tokens (E6, D-23).

The raw secret is shown once, at creation, and never stored: only a public
``prefix`` (indexed for lookup) and a SHA-256 hash of the full secret are kept
(D-30). Tokens authenticate the artifact REST API that agents call (T5/T6).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class PersonalAccessToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_tokens",
    )
    name = models.CharField(max_length=100, help_text="Human label, e.g. the client name.")
    prefix = models.CharField(max_length=16, unique=True)
    token_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user}:{self.name}"

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        return self.expires_at is not None and self.expires_at <= timezone.now()

    @property
    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired

    @property
    def display_prefix(self) -> str:
        return f"pln_{self.prefix}_…"

    def revoke(self) -> None:
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])
