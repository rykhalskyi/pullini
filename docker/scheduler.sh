#!/bin/sh
# Periodically synchronize projects (HLD §7).
#
# The poll cadence is just how often we check; each project is only synced once
# its own update interval has elapsed (see the sync_projects command).
set -e

interval="${SYNC_POLL_SECONDS:-60}"

while true; do
  python manage.py sync_projects || echo "sync run failed" >&2
  sleep "$interval"
done
