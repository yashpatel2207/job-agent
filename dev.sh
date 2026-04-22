#!/usr/bin/env bash
# Start backend API (uvicorn :8000) and frontend dashboard (next :3000) together.
# Ctrl+C stops both.
set -e

cd "$(dirname "$0")"
ROOT="$(pwd)"

if [ -f "$ROOT/backend/venv/Scripts/activate" ]; then
  VENV_ACT="$ROOT/backend/venv/Scripts/activate"
elif [ -f "$ROOT/backend/venv/bin/activate" ]; then
  VENV_ACT="$ROOT/backend/venv/bin/activate"
else
  echo "backend venv not found at $ROOT/backend/venv - run setup first" >&2
  exit 1
fi

(cd "$ROOT/backend" && source "$VENV_ACT" && exec uvicorn server:app --reload --port 8000) &
BACKEND_PID=$!

(cd "$ROOT/frontend" && exec npm run dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT INT TERM

wait
