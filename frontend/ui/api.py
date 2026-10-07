"""Read-only HTTP client for the portfolio backend API.

The frontend owns no database: every piece of content on the page is
fetched from the backend service over HTTP with httpx. Every failure mode
is translated into `PortfolioAPIError` so callers have one thing to catch.
"""

import httpx
from django.conf import settings


class PortfolioAPIError(RuntimeError):
    """The backend API was unreachable, errored, or returned a non-JSON body."""


def _get(path):
    """GET `path` from the backend and return the decoded JSON body.

    Raises:
        PortfolioAPIError: on a bad base URL, a transport failure, an error
            status, or a body that is not JSON. A proxy returning an HTML
            error page is what makes the last one more than theoretical.
            httpx.InvalidURL does not subclass httpx.HTTPError, so a bad
            PORTFOLIO_API_BASE_URL needs its own arm.
    """
    url = f"{settings.PORTFOLIO_API_BASE_URL}{path}"
    try:
        response = httpx.get(
            url,
            timeout=settings.PORTFOLIO_API_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, httpx.InvalidURL) as exc:
        raise PortfolioAPIError(f"GET {url} failed: {exc}") from exc
    except ValueError as exc:
        # json.JSONDecodeError subclasses ValueError, not httpx.HTTPError.
        raise PortfolioAPIError(f"GET {url} returned a non-JSON body: {exc}") from exc


def fetch_projects():
    """Return every portfolio project, ordered for display."""
    return _get("/api/projects/")


def fetch_skills():
    """Return every core skill, ordered for display."""
    return _get("/api/skills/")
