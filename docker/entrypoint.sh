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
fi

exec "$@"
