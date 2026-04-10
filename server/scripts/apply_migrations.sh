#!/usr/bin/env bash
set -euo pipefail

DB_URL="${DATABASE_URL:-}"
if [[ -z "${DB_URL}" ]]; then
  echo "DATABASE_URL is required" >&2
  exit 1
fi

for f in /app/migrations/*.sql; do
  echo "Applying $(basename "$f")"
  psql "${DB_URL}" -v ON_ERROR_STOP=1 -f "$f"
done

echo "Migrations applied."

