"""Views that render the portfolio from backend API data."""

import logging
from datetime import date
from functools import partial

from django.http import Http404
from django.shortcuts import render

from .api import (
    PortfolioAPIError,
    PortfolioNotFoundError,
    fetch_availability,
    fetch_project,
    fetch_projects,
    fetch_skills,
)

logger = logging.getLogger(__name__)

ALL_CATEGORIES = "ALL"

# The availability vocabulary the backend's `TextChoices` serves, named here
# because the panel treats two of the three words specially and a bare literal
# in a template cannot be found by a reader asking "where is `unstated`
# handled?". `UNSTATED` is the one state the panel HIDES -- it means nothing
# has been said, and a tag reading "SLOT: UNSTATED" would be noise where
# silence is the honest answer.
UNSTATED = "unstated"
OPEN = "open"

# The state tag's accent, decided once here and read twice by the template
# (`border-color` and `color`). Branching it inside the `style` attribute --
# which is what the API badge above it does -- would write the same condition
# twice in one tag, so the colour would have two sources of truth in a single
# attribute. `_skill_rows`' `bar_width` is the standing precedent for a
# presentation-only value computed in the view.
ACCENT_OPEN = "var(--ice)"
ACCENT_BOOKED = "var(--neon)"


def _safe(fetch):
    """Call `fetch`, returning None instead of raising when the API is down.

    A portfolio that 500s because its backend restarted is worse than one
    that renders an honest "API offline" panel, so the failure is logged and
    turned into an absent value. Each endpoint is fetched independently, so
    a skills outage does not discard projects that were retrieved fine.
    """
    try:
        return fetch()
    except PortfolioAPIError:
        logger.exception("Portfolio API unavailable; rendering offline state")
        return None


def _max_years(skills):
    """The panel's longest tenure, the scale every bar is drawn against.

    The alternative, a fixed ceiling such as ten years, is itself an invented
    number in a panel whose whole point is that it invents none.
    """
    return max((skill.get("years") or 0 for skill in skills), default=0)


def _bar_width(years, max_years):
    """Percent of the panel maximum, as a whole number; 0 when nothing is drawable.

    Both guards exist for one reason: `.xp-fill` declares no width of its own,
    so an absent or invalid `width` leaves it a block element drawing a FULL
    bar. A skill with no stored years would then display the longest bar on
    the panel -- the same fabricated statistic this story removes, wearing a
    different hat. `width:0%` is the honest empty track.
    """
    if not years or not max_years:
        return 0
    return round(years / max_years * 100)


def _skill_rows(skills):
    """Attach a presentation-only `bar_width` to each skill the API returned.

    A new dict per row, so the payload the API handed back is never mutated,
    and `years` keeps whatever the backend sent -- absent stays absent, so the
    template can tell "not stored" from a stored `0`.
    """
    max_years = _max_years(skills)
    return [
        {**skill, "bar_width": _bar_width(skill.get("years"), max_years)}
        for skill in skills
    ]


def _available_from(value):
    """The date the author is free from, or None when there is nothing to show.

    Three ways there is nothing to show, and each is a separate guard because
    each would otherwise fail differently:

    `None` or `""` is simply unset -- the author has stated a state without a
    date, which is a legitimate half-filled form.

    An unparseable value is a typo in an admin field. `date.fromisoformat`
    raises `ValueError` on "next month" or an impossible "2026-13-45", and
    `TypeError` if a backend ever sent a number instead of a string. Either
    would otherwise 500 the whole contact section -- the one part of the page
    that exists to be reachable -- over a mistyped field, so both are caught
    and the line is dropped instead.

    A date that has already arrived is the subtle one, and the reason this
    returns a date rather than the raw string: "AVAILABLE FROM NOVEMBER" read
    the following March is the stale sign on the door that makes a site look
    abandoned, and the availability line's whole commercial value is being
    current. Today counts as passed -- "from today" is just "now", and the
    state tag already says OPEN. Dropping the line rather than rewriting it to
    "now" keeps the panel from inventing copy the author did not write.
    """
    if not value:
        return None
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        logger.warning("Unparseable availability date %r; dropping the line", value)
        return None
    if parsed <= date.today():
        return None
    return parsed


def _hire_me_panel(payload):
    """Turn the availability object -- or an outage's None -- into context.

    The one place that knows this endpoint's shape, which is why the template
    carries no guard more complicated than "is this truthy". It is also the
    one place that must NOT assume a list: every other endpoint here returns a
    JSON array and this returns a single object, so a `for` loop written out
    of habit would iterate the payload's KEYS.

    An outage and an unconfigured site deliberately produce the same context.
    Both mean "nothing has been said about availability", and the panel has no
    honest way to distinguish them that a visitor would care about -- the hero
    badge and the project grid already report a backend outage, so saying it a
    third time here would be noise. What survives either way is the pitch line
    and the contact route, which are template copy: an outage must still leave
    a client able to send the email.
    """
    payload = payload or {}
    state = payload.get("state") or ""
    return {
        "availability_state": "" if state == UNSTATED else state,
        "availability_accent": ACCENT_OPEN if state == OPEN else ACCENT_BOOKED,
        "available_from": _available_from(payload.get("available_from")),
        "engagements": payload.get("engagements") or [],
    }


def home(request):
    """Render the full single-page portfolio.

    Three endpoints, each fetched independently so one outage never discards
    another's data. `api_online` is read from `projects` ALONE and deliberately
    not from the other two: it drives the `API OFFLINE` badge and the grid's
    `SIGNAL LOST` panel, so letting a dead availability singleton flip it would
    tell a visitor the whole site was down over the one endpoint whose absence
    the page is designed to absorb silently.
    """
    projects = _safe(fetch_projects)
    skills = _safe(fetch_skills)
    availability = _safe(fetch_availability)
    categories = sorted({project["category"] for project in projects or []})
    return render(
        request,
        "ui/home.html",
        {
            "projects": projects or [],
            "skills": _skill_rows(skills or []),
            "api_online": projects is not None,
            "categories": [ALL_CATEGORIES, *categories],
            "active_category": ALL_CATEGORIES,
            **_hire_me_panel(availability),
        },
    )


def _published_project(slug):
    """`fetch_project`, with a missing project raised as a real 404.

    This is the narrow half of the detail page's three outcomes, and it is a
    separate function so that it runs BEFORE `_safe` ever sees the exception.
    `PortfolioNotFoundError` subclasses `PortfolioAPIError`, so a single `try`
    whose arms were ever reordered would answer "the backend is down" to a
    simple typo -- the whole defect US-3.2 exists to make expressible. Nesting
    makes that ordering structural: there is no pair of arms to swap.

    `Http404` is deliberately outside the `PortfolioAPIError` hierarchy, so
    `_safe` does not catch it and it reaches Django's handler untouched. That
    is the property the composition rests on.
    """
    try:
        return fetch_project(slug)
    except PortfolioNotFoundError as exc:
        raise Http404(f"No published project with slug {slug!r}") from exc


def project_detail(request, slug):
    """Render one project as a case study, with three honest outcomes.

    Found renders the page; a missing slug is a real `404` raised above; any
    other API failure degrades to the same offline panel the home page shows,
    with a `200` -- a reachable site whose backend is briefly away is neither
    a missing page nor a crashed frontend.
    """
    project = _safe(partial(_published_project, slug))
    return render(
        request,
        "ui/project_detail.html",
        {"project": project, "api_online": project is not None},
    )


def project_grid(request):
    """Return just the project grid, filtered by category, for HTMX swaps."""
    projects = _safe(fetch_projects)
    active_category = request.GET.get("category", ALL_CATEGORIES)
    visible = [
        project
        for project in projects or []
        if active_category in (ALL_CATEGORIES, project["category"])
    ]
    return render(
        request,
        "ui/_project_grid.html",
        {
            "projects": visible,
            "api_online": projects is not None,
            "active_category": active_category,
        },
    )
