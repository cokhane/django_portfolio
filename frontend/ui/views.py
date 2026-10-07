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
            "skills": skills or [],
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
