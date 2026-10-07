# django_portfolio

A developer portfolio built as **two Django projects in one repository**: a
JSON API that owns the content, and a separate frontend that consumes it over
HTTP with [httpx](https://www.python-httpx.org/).

```
django_portfolio/
├── backend/      Django + DRF. Owns the database. Serves /api/. No templates.
├── frontend/     Django + httpx + HTMX. Owns the UI. No database.
└── requirements.txt
```

The two talk over HTTP only. The frontend has no models, no migrations and no
database connection — if it needs data, it asks the API.

## Running it

Both services run at once, in two terminals.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env          # DJANGO_DEBUG=1 for local work
```

`requirements.txt` includes `-e .`, which installs `portfolio_shared` — the
settings helpers both projects import.

**Terminal 1 — the API (port 8001):**

```bash
cd backend
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py seed_portfolio   # loads the projects and skills
../.venv/bin/python manage.py runserver 8001
```

**Terminal 2 — the site (port 8002):**

```bash
cd frontend
../.venv/bin/python manage.py runserver 8002
```

Then open <http://127.0.0.1:8002/>.

## API

| Endpoint | Returns |
|---|---|
| `GET /api/projects/` | Every project, ordered by `display_order` |
| `GET /api/skills/` | Every core skill, ordered by `display_order` |

Both endpoints are list-only and read-only: `POST`, `PUT` and `DELETE` return
`405`. Content is edited through the Django admin at
<http://127.0.0.1:8001/admin/>.

## Configuration

Both projects read their settings from `.env` via `portfolio_shared.env`,
which is **fail-closed**: `DEBUG` is off unless `DJANGO_DEBUG=1`, and with
debug off a missing `DJANGO_SECRET_KEY` raises `ImproperlyConfigured` at
startup rather than silently signing with a publicly known key.

| Variable | Used by | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | both | dev placeholder **only when `DJANGO_DEBUG=1`** |
| `DJANGO_DEBUG` | both | `0` (off) |
| `DJANGO_ALLOWED_HOSTS` | both | `127.0.0.1,localhost` |
| `PORTFOLIO_API_BASE_URL` | frontend | `http://127.0.0.1:8001` |
| `PORTFOLIO_API_TIMEOUT` | frontend | `5.0` seconds |

## When the API is down

The frontend does not return a 500. `ui.views._safe` wraps each API call,
logs the failure and yields `None` in place of the data, so degradation is
**per endpoint**: a skills outage still renders the projects it did fetch,
and only a projects outage replaces the grid with the `SIGNAL LOST` panel.
The `API OFFLINE` badge tracks the projects call. The site stays up either
way.

## Tests

```bash
cd backend  && ../.venv/bin/python manage.py test                     #  7 tests
cd backend  && ../.venv/bin/python manage.py test portfolio_shared    #  8 tests
cd frontend && ../.venv/bin/python manage.py test                     # 14 tests
```

The frontend tests use `SimpleTestCase` and mock the API layer, so they never
need the backend running.

## Deploying

The backend's WSGI entry point expects its own directory as the working dir,
e.g. `gunicorn --chdir backend mysite.wsgi`. Static files are served by the
web server from `STATIC_ROOT` after `manage.py collectstatic` — nothing in
the app serves them. The frontend's Tailwind CDN build is development-only
by Tailwind's own docs; compile a stylesheet before treating this as
production.
