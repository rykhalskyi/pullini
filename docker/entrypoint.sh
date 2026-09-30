#!/bin/sh
# Container entrypoint: apply migrations, collect static, then run the server.
set -e

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

exec "$@"
