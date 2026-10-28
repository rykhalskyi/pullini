---
created: 2026-10-17
type: ticket
status: implemented
summary: T16 — invite-link user onboarding: admins create users without passwords and share one-time setup links.
---

# T16 — Invite-link user onboarding

Builds on [T1 — Authorization](01-auth-login.md) and the accounts app from
[T3 — Personal Access Tokens](03-personal-access-tokens.md); records D-53.

## Spec

Administrators keep creating users in the Django admin, but must not choose or
know another person's password. The add form asks only for a username. On save,
Pullini creates the user with an unusable password and generates a **one-time
password setup link** that the admin copies and shares manually.

- The link is valid for one day (configurable with `PASSWORD_RESET_TIMEOUT`) and
  only once.
- The setup page enforces Django's configured password validators, then redirects
  to the login page.
- **Reset password & generate link** on the user change page removes the current
  password, invalidates existing sessions on their next request and every older
  setup link, then shows a fresh link.
- Links are signed with `SECRET_KEY` and tied to the user's password hash; no
  token rows or migrations are needed.
- The email field is not part of the token hash, so filling it in after
  generating the link does not break the invite.
- No email delivery: the admin copies the link from the user page.

## Plan

1. `accounts/invites.py`: namespaced setup-token generator, `uidb64` helpers,
   absolute URL builder, and session key for the one-time link flash.
2. `settings.py`: `PASSWORD_RESET_TIMEOUT` defaulting to 86400 seconds.
3. Public `accounts/set-password/<uidb64>/<token>/` view using `SetPasswordForm`;
   setup + invalid-link templates.
4. `accounts/forms.py`: `InviteUserCreationForm` with no password fields;
   `PulliniUserAdmin` replaces Django's `UserAdmin`, forcing unusable passwords
   on add.
5. Admin action `auth_user_setup_link` (POST, admin-only) resets the password and
   issues a new link; custom user change/add templates show it once with a copy
   button and add a password-status column.
6. Tests for the add form, one-time/expired/tampered links, password rules,
   admin reset and permission checks.
7. Update README, `.env.example`, decision record and wiki index/log.

## Outcome

Implemented. Admins create users with only a username; `PulliniUserAdmin` sets an
unusable password and flashes a one-time setup URL in the session after saving.
The public `password_setup` view validates the signed token (active user, no
usable password, within the one-day timeout) and uses `SetPasswordForm`, then
redirects to login. **Reset password & generate link** calls
`set_unusable_password()`, which invalidates existing sessions and previous
signed links, then flashes a fresh URL. The admin user list shows whether a
password is set, and no database migration is required.
