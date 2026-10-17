"""Admin form for inviting a user without choosing a password for them."""

from __future__ import annotations

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class InviteUserCreationForm(forms.ModelForm):
    """Create only the username; the user sets their password via a link."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    def clean_username(self):
        return UserCreationForm.clean_username(self)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
            self.save_m2m()
        return user
