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
need the backend running. All three suites need a `.env` to exist first — the
settings are fail-closed, so without one they refuse to start rather than fall
back to a known key.

## Linting

`ruff` covers the whole tree in one pass. `pylint` cannot: there are two Django
projects here, each with its own settings module, and neither is importable from
the repo root. So it runs once per target, naming the settings that target needs.

Run all of these **from the repository root** — the pylint config puts both
service directories on `sys.path` using paths relative to it.

```bash
.venv/bin/python -m ruff check .

.venv/bin/python -m pylint --django-settings-module=mysite.settings        portfolio_shared
.venv/bin/python -m pylint --django-settings-module=mysite.settings        backend
.venv/bin/python -m pylint --django-settings-module=frontend_site.settings frontend
```

Each must score `10.00/10`.

Linting both services in a single invocation instead reports `R0801`
duplicate-code between them, in three places: the two `manage.py` files, the two
`TEMPLATES` blocks, and the two i18n blocks (`LANGUAGE_CODE`, `TIME_ZONE`,
`USE_I18N`, `USE_TZ`). All three are Django's own generated scaffolding, present
in every Django project, and merging them would be the wrong abstraction — the
`TEMPLATES` blocks are not even identical, since only the backend needs the auth
and messages context processors for the admin.

What that report must **not** be used to excuse is hand-written duplication. The
settings contract the two projects genuinely share — loading `.env`, then
deriving `DEBUG`, then the signing key *from* `DEBUG`, then the host allowlist —
is wiring this repository wrote, not scaffolding Django generated, so it lives
in `portfolio_shared.env.environment_settings()` and each `settings.py` calls it
in one line. It was duplicated until that extraction, and splitting the lint runs
would have hidden it rather than fixed it.

## Deploying

The backend's WSGI entry point expects its own directory as the working dir,
e.g. `gunicorn --chdir backend mysite.wsgi`. Static files are served by the
web server from `STATIC_ROOT` after `manage.py collectstatic` — nothing in
the app serves them. The frontend's Tailwind CDN build is development-only
by Tailwind's own docs; compile a stylesheet before treating this as
production.
