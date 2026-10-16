"""Read-only HTTP client for the portfolio backend API.

The frontend owns no database: every piece of content on the page is
fetched from the backend service over HTTP with httpx. Every failure mode
is translated into `PortfolioAPIError` so callers have one thing to catch.
A 404 additionally gets the `PortfolioNotFoundError` subclass, so a caller
that asked for one named resource can tell "it does not exist" apart from
"the API is down" without any other caller having to change.
"""

from http import HTTPStatus

import httpx
from django.conf import settings


class PortfolioAPIError(RuntimeError):
    """The backend API was unreachable, errored, or returned a non-JSON body."""


class PortfolioNotFoundError(PortfolioAPIError):
    """The backend answered 404: the one named resource does not exist.

    Catch this only around a fetch of ONE named resource (a project by
    slug). A 404 on a list route means the API is misconfigured, which is an
    outage and not a missing project -- the distinction is about what was
    requested, which only the caller knows. Every caller that does not opt in
    keeps catching the parent and keeps behaving exactly as before, because
    this is a subclass.
    """


def _get(path):
    """GET `path` from the backend and return the decoded JSON body.

    Raises:
        PortfolioNotFoundError: when the backend answers 404.
        PortfolioAPIError: on a bad base URL, a transport failure, any other
            error status, or a body that is not JSON. A proxy returning an HTML
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
    except httpx.HTTPStatusError as exc:
        # This arm must stay above the broad one: HTTPStatusError subclasses
        # HTTPError and Python takes the first matching arm, so swapping the
        # two would leave this one unreachable.
        message = f"GET {url} failed: {exc}"
        if exc.response.status_code == HTTPStatus.NOT_FOUND:
            raise PortfolioNotFoundError(message) from exc
        raise PortfolioAPIError(message) from exc
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


def fetch_availability():
    """Return the author's availability statement and its engagement cards.

    The only endpoint here that answers with an OBJECT rather than a list, so
    a caller must not iterate the result or treat an empty one as "no rows":
    `{"state": ..., "available_from": ..., "engagements": [...]}`.

    There is no not-found case to distinguish. Availability is a singleton the
    backend serves from an unsaved default when nothing has been filled in, so
    an unconfigured site answers `200` with the empty shape rather than `404`
    -- which is why this takes no `PortfolioNotFoundError` arm and why callers
    wrap it in `_safe` rather than in the detail page's narrower handling.
    """
    return _get("/api/availability/")


def fetch_project(slug):
    """Return one published project as its whole case study.

    Raises:
        PortfolioNotFoundError: no published project has this slug. A draft
            and a slug that was never used are the same answer here, which is
            the backend's design rather than an omission -- its published
            filter is a queryset, so a draft is never found rather than found
            and refused.
        PortfolioAPIError: any other failure, as everywhere else.

    The `<slug:slug>` URL converter admits only `[-a-zA-Z0-9_]`, so the slug
    reaches this point already constrained to characters that need no quoting.
    """
    return _get(f"/api/projects/{slug}/")
