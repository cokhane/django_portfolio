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
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env          # DJANGO_DEBUG=1 for local work
```

`requirements-dev.txt` pulls in `requirements.txt` and adds the gate's tools at
pinned versions. `requirements.txt` alone is enough to merely run the two
services; it includes `-e .`, which installs `portfolio_shared` — the settings
helpers both projects import.

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
cd backend  && ../.venv/bin/python manage.py test                     #  46 tests
cd backend  && ../.venv/bin/python manage.py test portfolio_shared    #  12 tests
cd frontend && ../.venv/bin/python manage.py test                     # 246 tests
```

The frontend tests use `SimpleTestCase` and mock the API layer, so they never
need the backend running. All three suites need a `.env` to exist first — the
settings are fail-closed, so without one they refuse to start rather than fall
back to a known key.

The counts above are a snapshot, measured 2026-10-26. CI asserts that the suites
pass, never how many tests there are — a number committed to a workflow rots the
first time anyone adds one.

### Coverage

On a pull request the suites run *through* coverage. These six lines are what CI
runs; they replace the three above rather than joining them, so nothing is run
twice:

```bash
cd backend  && ../.venv/bin/python -m coverage run --source=. --append manage.py test
cd backend  && ../.venv/bin/python -m coverage run --source=portfolio_shared --append manage.py test portfolio_shared
cd frontend && ../.venv/bin/python -m coverage run --source=. --append manage.py test

.venv/bin/python -m coverage combine backend/.coverage frontend/.coverage
.venv/bin/python -m coverage xml
.venv/bin/diff-cover coverage.xml --compare-branch=origin/main --fail-under=100
```

**Each line starts from the repository root**, exactly as in the block above —
the `cd` does not carry over, so pasting the three run lines in one shell fails
on the second. In CI each is a separate step, which starts at the root anyway.

Three details here are load-bearing, and all three are easy to get wrong:

- **`--source` is a flag, not config.** Coverage looks for its configuration in
  the current directory and does not walk up, so a run started in `backend/`
  never reads `pyproject.toml` at all. `--source` also makes a module that no
  test imports appear in the report at 0% instead of being absent from it, which
  is the difference between a new untested file failing the gate and sailing
  through it.
- **`combine` before `xml`.** Two of the runs start from `backend/` and one from
  `frontend/`, so they write two separate data files; `combine` merges them and
  deletes its inputs. The `xml` step then runs from the root, and *that* is what
  makes the paths inside `coverage.xml` repo-root-relative — which is the only
  reason `diff-cover` can match them against the paths git reports for the diff.
  Setting `relative_files` instead does not work here: the paths come out
  relative to `backend/`, and `coverage xml` then dies on `No source for code:
  'manage.py'`.
- **`diff-cover` is a console script.** `python -m diff_cover` has no entry
  point and fails with `No module named diff_cover.__main__`.

The threshold is **100% of the lines the pull request changed**, not of the
repository. Total coverage is deliberately not gated: there is untested Django
scaffolding here, and a total threshold would force either a growing exclusion
list or a number chosen to make it pass. `# pragma: no cover` is a suppression
like any other and is not used — a line that cannot be covered is usually a line
that wants reshaping, which is the point of measuring.

`[tool.coverage.report]` in `pyproject.toml` holds the omit list — migrations,
`manage.py`, `wsgi.py`, `asgi.py` and the settings modules. It is read only by
the `coverage xml` step, the one that runs from the root.

## Linting

`ruff` covers the whole tree in one pass. `pylint` cannot: there are two Django
projects here, each with its own settings module, and neither is importable from
the repo root. So it runs once per target, naming the settings that target needs.

`flake8` runs as well, and is not redundant with `ruff`. Ruff's *stable* `E`
rules are E4, E5, E7 and E9; pycodestyle's logical-line checks E1, E2 and E3 are
still preview-only there, so flake8 is at present the only tool enforcing them.

Run all of these **from the repository root** — the pylint config puts both
service directories on `sys.path` using paths relative to it.

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m flake8

.venv/bin/python -m pylint --fail-under=10.0 --django-settings-module=mysite.settings        portfolio_shared
.venv/bin/python -m pylint --fail-under=10.0 --django-settings-module=mysite.settings        backend
.venv/bin/python -m pylint --fail-under=10.0 --django-settings-module=frontend_site.settings frontend
```

Each must score `10.00/10`. `--fail-under` is pylint's own default; it is stated
explicitly so the bar is visible in the log rather than inherited silently.

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

## Continuous integration

Every pull request runs the gate above — `ruff`, `flake8`, the three `pylint`
targets, all three test suites, and then coverage on the lines that pull request
changed — from [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Lint,
tests and coverage only: there is deliberately no deploy, publish or release
step, the deployment half of the project being parked.

**The checkout is not shallow.** `fetch-depth: 0` is set because `diff-cover`
diffs the branch against `origin/main`, and the default depth-1 checkout has no
`origin/main` to diff against — it fails on a missing revision, which reads like
a broken tool rather than the one-line checkout setting it is.

**The workflow's commands are copied verbatim from this file**, venv and all.
That is why the job builds a `.venv` on a runner that is already isolated: it
lets the commands here and the commands in CI be character-for-character the
same, so a local pass and a CI failure cannot disagree about what the gate is.
Change a command in one place and change it in the other in the same commit —
nothing enforces that automatically.

**The tool versions are pinned in [`requirements-dev.txt`](requirements-dev.txt)**,
not in the workflow. Installing them unpinned would let a new `pylint` release
turn up a new check and fail a pull request that changed nothing — a tool upgrade
arriving disguised as a code regression. Upgrading is therefore an edit to that
file, reviewed like any other.

**Python is pinned to 3.14**, one version, no matrix: it is the interpreter every
number in this file was measured on. `pyproject.toml`'s
`requires-python = ">=3.11"` is not a competing answer, because it is not true —
`requirements.txt` pins Django 6.1.2, whose own metadata requires `>=3.12`, so
3.11 could never have installed. That floor is stale and wants correcting on its
own terms; nothing in CI depends on it.

On a pull request the check reports as **`CI / lint-and-test`**. That is the name
to use if it is ever made a required status check — a repository setting, not a
file in here.

## Static files

Two committed assets live under `frontend/ui/static/ui/`: the CV, and
`tailwind.css` — the compiled stylesheet described in the next section.

The CV lives at `frontend/ui/static/ui/cv.pdf` and is linked from the
hire-me panel with `{% static %}`, so it resolves to `/static/ui/cv.pdf`.
It is found by `django.contrib.staticfiles`' app-directory discovery —
`STATICFILES_DIRS` is deliberately not set. The stored name is role-shaped
rather than versioned so a revised CV replaces the file without moving the
URL; the `download` attribute carries the name the visitor's browser saves
it as, independently of the path.

**`runserver` serves this only while `DJANGO_DEBUG=1`.** In production the
link 404s until `collectstatic` has run and a web server serves the result —
and the frontend sets no `STATIC_ROOT` yet, so that is the first thing a
deployment needs. How the site is deployed is still an open question, so
nothing here assumes an answer.

## Regenerating the stylesheet

`frontend/ui/static/ui/tailwind.css` is a **generated file, committed on
purpose, never hand-edited**. It replaced an unversioned, development-only
CDN script — 407 KB of third-party JavaScript with full access to the page
and no integrity hash possible — with the 17 KB of CSS that script was
producing.

Run this from `django_portfolio/` after changing any `class="…"` in a
template:

```bash
{ sed -n '1,/^ \*\//p' frontend/ui/static/ui/tailwind.css; printf '\n'
  npx -y tailwindcss@3.4.17 --content 'frontend/**/*.html'
  printf '\n'
} > /tmp/tailwind.css && mv /tmp/tailwind.css frontend/ui/static/ui/tailwind.css
```

The first line re-emits the file's own provenance header — matched up to
its closing `*/` rather than by a line count, so editing the header cannot
silently truncate it — and the second regenerates the rules. **The version is pinned deliberately** — an
unversioned build is the defect this replaced, so an upgrade should be a
visible change to that number and to `SHEET_VERSION` in
`ui/test_stylesheet.py`. Node is used only here, on the author's machine:
nothing Node-shaped is committed, there is no `package.json`, no lockfile
and no CI step, and the repository stays Python. Where Node is unavailable,
Tailwind's standalone CLI binary at the same version produces the same file.
The command reads only local templates and needs **no secret, token or
credential** (NFR-3).

**You do not have to remember to run it.** `ui/test_stylesheet.py` fails,
naming the offending class, whenever a class the page applies has no rule in
either the inline `<style>` block in `base.html` or this file. That covers
the two ways a generated stylesheet silently stops matching its markup: a
template the scan never read, and a class applied only from JavaScript —
which the generator cannot see, because it reads `class="…"` out of the
templates.

The JavaScript half needs two mechanisms, because one cannot reach all of
it. `classList.toggle("no-motion")` writes the name down, so the test reads
it out of the script text. `classList.add(worlds[name])` and
`classList.add(STRUCK)` do not, and no amount of scanning recovers a string
that is never written — so those four (`manor`, `horror`, `clean`,
`struck`) are listed by name in `COMPUTED_SCRIPT_CLASSES` and asserted
individually. A derived check that silently skipped them would have been
worse than a list that admits what it is.

**One deliberate overlap.** The sheet carries Tailwind's preflight, which
restates a few rules the inline `<style>` block already had — `box-sizing`,
`body{margin:0}`, `a{color:inherit}` and two `[hidden]` rules. They set the
same values, so the cascade is unchanged, and they were left in place
because this change's contract was that nothing visual may change. Retiring
them is a follow-up with its own before-and-after comparison.

Two details worth knowing before reading the file. It is **unminified**, so
it diffs — a reviewer can see what a regeneration changed, which is the
whole point of committing it. And it carries about 21 single-declaration
rules for classes nothing uses (`container`, `table`, `ring`, `filter`…):
Tailwind's scanner matches bare words in prose and CSS, not just class
attributes, so it invents them. They cost under 1 KB and collide with
nothing. Suppressing them would mean adding a `tailwind.config.js` — a
JavaScript file in a Python repository, to silence under 1 KB of dead CSS.

## Deploying

The backend's WSGI entry point expects its own directory as the working dir,
e.g. `gunicorn --chdir backend mysite.wsgi`. Static files are served by the
web server from `STATIC_ROOT` after `manage.py collectstatic` — nothing in
the app serves them — including `tailwind.css`, which is an ordinary
committed static file like the CV and needs no build step at deploy time.
If minified CSS is wanted, that belongs to whatever serves static files,
not to the repository.
