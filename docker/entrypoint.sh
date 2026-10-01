#!/bin/sh
# Container entrypoint: apply migrations, collect static, then run the server.
# Set PULLINI_SKIP_BOOTSTRAP=true for secondary containers (e.g. the scheduler)
# that share the database and volume but must not migrate concurrently.
set -e

if [ "${PULLINI_SKIP_BOOTSTRAP:-false}" != "true" ]; then
  attempt=1
  until python manage.py migrate --noinput; do
    if [ "$attempt" -ge 10 ]; then
      echo "migrate failed after ${attempt} attempts" >&2
      exit 1
    fi
    echo "waiting for database (attempt ${attempt})..." >&2
    attempt=$((attempt + 1))
    sleep 2
  done

  python manage.py collectstatic --noinput

  # Seed the single admin user (HLD V1 principle 3) from the environment.
  # Idempotent: an existing user is left untouched, so this is safe on every
  # start. Credentials live in the platform's secret store, never in the image.
  if [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    python manage.py shell -c "
import os
from django.contrib.auth import get_user_model

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
if User.objects.filter(username=username).exists():
    print(f'superuser {username!r} already exists')
else:
    User.objects.create_superuser(
        username,
        os.environ.get('DJANGO_SUPERUSER_EMAIL', ''),
        os.environ['DJANGO_SUPERUSER_PASSWORD'],
    )
    print(f'created superuser {username!r}')
"
  fi
fi

exec "$@"
