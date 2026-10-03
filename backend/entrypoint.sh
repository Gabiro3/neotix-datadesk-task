#!/bin/sh
set -e
cd /app
alembic upgrade head
python -m app.cli seed
if [ -f /app/seed/episodes.csv ]; then
  python -m app.cli import /app/seed/episodes.csv || true
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
