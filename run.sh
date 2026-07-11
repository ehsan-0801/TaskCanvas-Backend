#!/usr/bin/env bash
# Start the TaskCanvas Django backend.
# Usage:
#   ./run.sh              start server on port 8000
#   ./run.sh 8080         start server on port 8080
#   ./run.sh --migrate    run migrations first, then start (port 8000)
#   ./run.sh --migrate 8080
set -euo pipefail

cd "$(dirname "$0")"

PY=".venv/bin/python"
MIGRATE=false

# Optional --migrate flag (in any position).
ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--migrate" ]]; then
    MIGRATE=true
  else
    ARGS+=("$arg")
  fi
done

PORT="${ARGS[0]:-8000}"

if [[ "$MIGRATE" == true ]]; then
  "$PY" manage.py migrate
fi

"$PY" manage.py runserver "127.0.0.1:${PORT}"
