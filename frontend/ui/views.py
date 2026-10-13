"""Views that render the portfolio from backend API data."""

import logging

from django.shortcuts import render

from .api import PortfolioAPIError, fetch_projects, fetch_skills

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
