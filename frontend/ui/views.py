"""Views that render the portfolio from backend API data."""

import logging
from functools import partial

from django.http import Http404
from django.shortcuts import render

from .api import (
    PortfolioAPIError,
    PortfolioNotFoundError,
    fetch_project,
    fetch_projects,
    fetch_skills,
)

logger = logging.getLogger(__name__)

ALL_CATEGORIES = "ALL"


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


def home(request):
    """Render the full single-page portfolio."""
    projects = _safe(fetch_projects)
    skills = _safe(fetch_skills)
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
