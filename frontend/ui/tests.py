"""Tests for the frontend API client and its views."""

from unittest.mock import patch

import httpx
from django.test import SimpleTestCase
from django.urls import reverse

from .api import PortfolioAPIError, fetch_projects

PROJECTS = [
    {
        "id": 1,
        "title": "E-Commerce Platform",
        "category": "Web App",
        "description": "A full-featured online store.",
        "tech_stack": ["Django", "React"],
    },
    {
        "id": 2,
        "title": "Tech Blog Platform",
        "category": "Blog",
        "description": "Modern blogging platform.",
        "tech_stack": ["Django", "Tailwind"],
    },
]
SKILLS = [{"id": 1, "name": "Django / Python / FastApi"}]

_REQUEST = httpx.Request("GET", "http://testserver/api/projects/")


class APIClientTests(SimpleTestCase):
    """`ui.api` is the only place the frontend talks HTTP."""

    @patch("ui.api.httpx.get")
    def test_transport_errors_surface_as_portfolio_api_error(self, mock_get):
        """A refused connection becomes PortfolioAPIError."""
        mock_get.side_effect = httpx.ConnectError("refused")

        with self.assertRaises(PortfolioAPIError):
            fetch_projects()

    @patch("ui.api.httpx.get")
    def test_timeouts_surface_as_portfolio_api_error(self, mock_get):
        """A slow backend becomes PortfolioAPIError rather than hanging."""
        mock_get.side_effect = httpx.ReadTimeout("too slow")

        with self.assertRaises(PortfolioAPIError):
            fetch_projects()

    @patch("ui.api.httpx.get")
    def test_error_statuses_surface_as_portfolio_api_error(self, mock_get):
        """A 5xx response becomes PortfolioAPIError."""
        mock_get.return_value = httpx.Response(500, request=_REQUEST)

        with self.assertRaises(PortfolioAPIError):
            fetch_projects()

    @patch("ui.api.httpx.get")
    def test_non_json_bodies_surface_as_portfolio_api_error(self, mock_get):
        """A proxy's HTML error page must not escape as a raw ValueError.

        json.JSONDecodeError subclasses ValueError, not httpx.HTTPError, so
        without its own except arm this would 500 the page.
        """
        mock_get.return_value = httpx.Response(
            200, text="<html>502 Bad Gateway</html>", request=_REQUEST
        )

        with self.assertRaises(PortfolioAPIError):
            fetch_projects()

    @patch("ui.api.httpx.get")
    def test_malformed_base_urls_surface_as_portfolio_api_error(self, mock_get):
        """A bad PORTFOLIO_API_BASE_URL is config error, not a crash."""
        mock_get.side_effect = httpx.InvalidURL("no host")

        with self.assertRaises(PortfolioAPIError):
            fetch_projects()


@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class HomeViewTests(SimpleTestCase):
    """The home page renders whatever the API returned."""

    def test_renders_every_project_from_the_api(self, *_mocks):
        """Each project returned by the API reaches the page."""
        response = self.client.get(reverse("ui:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E-Commerce Platform")
        self.assertContains(response, "Tech Blog Platform")

    def test_builds_a_filter_button_per_category(self, *_mocks):
        """Categories are derived from the data, ALL first."""
        response = self.client.get(reverse("ui:home"))

        self.assertEqual(
            response.context["categories"], ["ALL", "Blog", "Web App"]
        )

    def test_renders_skills_from_the_api(self, *_mocks):
        """The CORE SKILLS panel is API-driven too."""
        response = self.client.get(reverse("ui:home"))

        self.assertContains(response, "Django / Python / FastApi")


@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class PositioningTests(SimpleTestCase):
    """The positioning copy is the deliverable, so it gets a regression guard.

    Every other test here asserts API-driven content. The hero, the pitch and
    the contact address are static template text, so a revert or a typo would
    pass the whole suite silently -- which is exactly how a site goes back to
    selling a junior version of its author without anyone noticing.
    """

    def test_the_hero_states_the_discipline(self, *_mocks):
        """The hero reads SOLUTION ARCHITECT, not DEVELOPER & DESIGNER."""
        response = self.client.get(reverse("ui:home"))

        self.assertContains(response, "SOLUTION")
        self.assertContains(response, "ARCHITECT")
        self.assertNotContains(response, "DESIGNER")

    def test_contact_uses_the_personal_address(self, *_mocks):
        """A site soliciting freelance work does not route to an employer."""
        response = self.client.get(reverse("ui:home"))

        self.assertContains(response, "rhidzkhan.ahmad99@gmail.com")

    def test_the_employer_address_is_gone(self, *_mocks):
        """The specific defect was an address, so the guard is on the address."""
        response = self.client.get(reverse("ui:home"))

        self.assertNotContains(response, "anervea.ai")

    def test_the_years_figure_is_the_one_g9_settled(self, *_mocks):
        """BRD G9 chose 11 over the CV's hedged "10+".

        The page states the figure twice: in words in the pitch, and in digits
        in the stat tile. A number corrected in one and not the other is wrong
        on the same screen, so both forms are asserted, and positively -- a
        check for the absence of the old figure would pass just as happily on
        a page that had lost it altogether.

        The tile is matched by its label and its value, with any attributes
        allowed through. Pinning the class list instead would turn every
        restyle -- four themes in epic 5, a compiled stylesheet in US-7.2 --
        into a failure with no copy regression behind it, and a guard that
        cries wolf is one somebody eventually deletes.
        """
        response = self.client.get(reverse("ui:home"))

        self.assertContains(response, "Eleven years")
        self.assertRegex(
            response.content.decode(),
            r"YEARS ACTIVE</p>\s*<p[^>]*>11</p>",
        )


class HomeViewOutageTests(SimpleTestCase):
    """An API outage degrades the page instead of breaking it."""

    @patch("ui.views.fetch_skills", side_effect=PortfolioAPIError("down"))
    @patch("ui.views.fetch_projects", side_effect=PortfolioAPIError("down"))
    def test_degrades_to_an_offline_state_instead_of_erroring(self, *_mocks):
        """A full outage renders 200 with SIGNAL LOST, not a 500."""
        response = self.client.get(reverse("ui:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SIGNAL LOST")

    @patch("ui.views.fetch_skills", side_effect=PortfolioAPIError("down"))
    @patch("ui.views.fetch_projects", return_value=PROJECTS)
    def test_a_skills_outage_still_renders_the_projects(self, *_mocks):
        """Each endpoint fails independently; one outage is not total."""
        response = self.client.get(reverse("ui:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "E-Commerce Platform")


@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ProjectGridTests(SimpleTestCase):
    """The HTMX partial filters the same data without a page load."""

    def test_filters_to_the_requested_category(self, _mock):
        """Only projects in the requested category are rendered."""
        response = self.client.get(
            reverse("ui:project-grid"), {"category": "Blog"}
        )

        self.assertContains(response, "Tech Blog Platform")
        self.assertNotContains(response, "E-Commerce Platform")

    def test_all_keeps_every_project(self, _mock):
        """The ALL pseudo-category filters nothing out."""
        response = self.client.get(
            reverse("ui:project-grid"), {"category": "ALL"}
        )

        self.assertContains(response, "Tech Blog Platform")
        self.assertContains(response, "E-Commerce Platform")

    def test_defaults_to_all_when_no_category_is_given(self, _mock):
        """A missing category parameter behaves like ALL."""
        response = self.client.get(reverse("ui:project-grid"))

        self.assertContains(response, "E-Commerce Platform")

    @patch("ui.views.fetch_skills")
    def test_does_not_fetch_skills_it_would_discard(self, mock_skills, _mock):
        """The grid endpoint only fetches what it renders."""
        self.client.get(reverse("ui:project-grid"))

        mock_skills.assert_not_called()
