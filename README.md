# Dataset Request Desk

Internal platform for a robotics data-collection company: clients submit dataset requests, operators assign episodes, clients accept or reject deliveries.

**Stretch item:** real-time request updates for operators (SSE over an authenticated stream).

## Run everything

```bash
docker compose up --build
```

- API: http://localhost:8000
- UI: http://localhost:3000  (not 8080 — that port is often taken by Oracle XE on Windows)
- Health: http://localhost:8000/health

The API container runs migrations, seeds users, and imports `seed/episodes.csv` on startup.

## Seed logins

| Email | Password | Role |
|---|---|---|
| admin@example.com | admin123 | admin |
| ops1@example.com | ops123 | operator |
| ops2@example.com | ops123 | operator |
| client-a@example.com | client123 | client |
| client-b@example.com | client123 | client |

Passwords are hashed with bcrypt before insert. They are not stored in plaintext.
Users created by an administrator receive a temporary password and must replace it on first login before any application endpoint is available.

## Local development (optional)

PostgreSQL must be running (compose `db` service is enough).

```bash
# backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://desk:desk@localhost:5432/desk
export JWT_SECRET=dev-secret-change-me
alembic upgrade head
python -m app.cli seed
python -m app.cli import ../seed/episodes.csv
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev
```

Vite proxies API calls to port 8000.

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest -q
```

Tests use an in-memory SQLite database. They cover authorization, status transitions, assignment rules, and CSV import idempotency.

## CSV import

`POST /episodes/import` (operator/admin) or:

```bash
python -m app.cli import path/to/episodes.csv
```

The importer is safe to re-run. It reports imported / updated / skipped rows and a reason for every skip. Rules are documented in `NOTES.md`.

## Analytics

`GET /analytics?start=2026-08-01T00:00:00Z&end=2026-09-30T23:59:59Z`

All three aggregations run in SQL:

- episodes recorded per day, per robot
- request counts by status, plus median hours from first `submitted` event to first `delivered` event (`percentile_cont`)
- top 5 task names by count of `good` episodes

At ~5 million episodes these stay index-friendly: `episodes(recorded_at, robot_id)`, `episodes(task_name, quality)`, and `request_events(to_status, request_id, created_at)`. Median uses a grouped event subquery, not a Python scan. At that size you would still want a date-partitioned `episodes` table (or a daily rollup) so analytics does not sit on the OLTP heap.

## API shape

| Method | Path | Who |
|---|---|---|
| POST | `/auth/login` | public |
| GET | `/auth/me` | any user |
| GET/POST | `/requests` | client sees own; staff sees all. Only clients create. |
| GET | `/requests/{id}` | owner or staff |
| POST | `/requests/{id}/transition` | role-checked |
| POST/DELETE | `/requests/{id}/assignments` | operator/admin |
| GET | `/episodes` | operator/admin |
| POST | `/episodes/import` | operator/admin |
| GET | `/analytics` | operator/admin |
| GET/POST/PATCH | `/users` | admin |
| GET | `/events` | operator/admin (SSE) |
| GET | `/health` | public |

## Logging

One structured line per request:

`method=GET path=/requests status=200 duration_ms=12.4 user_id=3`
