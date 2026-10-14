"""Tests for the frontend API client and its views."""

import re
from unittest.mock import patch

import httpx
from django.test import SimpleTestCase
from django.urls import reverse

from .api import PortfolioAPIError, PortfolioNotFoundError, fetch_projects

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
SKILLS = [
    {"id": 1, "name": "Python / Django / FastAPI", "years": 10, "is_primary_focus": False},
    {"id": 2, "name": "AI / LLM Platforms", "years": 2, "is_primary_focus": True},
]
# A backend deployed before US-2.2-BE added the fields: no `years`, no focus flag.
LEGACY_SKILLS = [{"id": 1, "name": "Django / Python / FastApi"}]

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

    def test_not_found_is_a_portfolio_api_error(self):
        """The subclass relationship is the property every other caller rests on.

        `_safe` catches the parent, and both outage tests raise the parent.
        A sibling exception would slip past all of them silently, so the
        hierarchy is asserted directly rather than inferred from behaviour.
        """
        self.assertTrue(issubclass(PortfolioNotFoundError, PortfolioAPIError))

    @patch("ui.api.httpx.get")
    def test_a_404_surfaces_as_not_found(self, mock_get):
        """BRD F2: a missing resource must reach the caller as its own type.

        Without this the only honest answer to a typo'd project URL is the
        SIGNAL LOST panel, which tells a prospective client the backend is
        down. The message still names the path, so a log line stays
        diagnosable -- the path rather than the whole URL, because the base
        URL is environment config and the path is the constant under test.
        """
        mock_get.return_value = httpx.Response(404, request=_REQUEST)

        with self.assertRaises(PortfolioNotFoundError) as caught:
            fetch_projects()

        self.assertIn("/api/projects/", str(caught.exception))

    @patch("ui.api.httpx.get")
    def test_a_500_is_not_a_not_found(self, mock_get):
        """The negative is the half that matters.

        A classifier that returned the narrow type for every error status
        would pass the 404 test above and still tell a visitor the site is
        missing while the backend is merely down.
        """
        mock_get.return_value = httpx.Response(500, request=_REQUEST)

        with self.assertRaises(PortfolioAPIError) as caught:
            fetch_projects()

        self.assertNotIsInstance(caught.exception, PortfolioNotFoundError)

    @patch("ui.api.httpx.get")
    def test_the_parent_arm_still_catches_a_404(self, mock_get):
        """Every existing caller is provably unaffected by the new type.

        `_safe` catches `PortfolioAPIError` and nothing else. If this stopped
        holding, a 404 on the list route -- a misconfigured API, not a missing
        project -- would escape as a 500 instead of degrading to SIGNAL LOST.
        """
        mock_get.return_value = httpx.Response(404, request=_REQUEST)

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

        self.assertContains(response, "Python / Django / FastAPI")


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


@patch("ui.views.fetch_projects", return_value=PROJECTS)
class SkillsPanelTests(SimpleTestCase):
    """Every number in CORE SKILLS is stored data, and none is list position.

    The panel used to render `LV.{{ forloop.revcounter }}` and size its bar
    from the same counter, so reordering the list in admin silently rewrote
    every "level". These tests pin the replacement and, just as importantly,
    the two ways it could fabricate a new number in place of the old one: a
    stored `0` read as "absent", and a zero scale drawing a full bar.
    """

    def _rendered_widths(self, skills):
        """Map each skill name to the bar width the PAGE actually draws for it.

        Read off the HTML rather than `response.context`, because the context
        is the half of this change that is already honest. A template that
        went back to `{% widthratio forloop.revcounter %}` while the view
        carried on computing a correct `bar_width` would satisfy any
        context-based assertion and still ship the exact defect this story
        exists to remove. Only the rendered attribute proves what a visitor
        is shown. The panel is sliced out first so the page's other bare
        `<span>`s cannot be paired with a skill's track.
        """
        with patch("ui.views.fetch_skills", return_value=skills):
            response = self.client.get(reverse("ui:home"))
        panel = response.content.decode().split("CORE SKILLS")[1].split("// PROJECTS")[0]
        return dict(re.findall(r"<span>([^<]+)</span>.*?width:(\d+)%", panel, re.S))

    @patch("ui.views.fetch_skills", return_value=SKILLS)
    def test_the_fabricated_level_badge_is_gone(self, *_mocks):
        """`LV.N` is replaced by the stored years figure."""
        response = self.client.get(reverse("ui:home"))

        self.assertNotContains(response, "LV.")
        self.assertContains(response, "10 YRS")
        self.assertContains(response, "2 YRS")

    def test_bar_widths_are_drawn_from_years(self, *_mock):
        """The longest tenure fills the track and the rest scale against it.

        10 and 2 years are chosen so the answer is one list position could
        not have produced: `forloop.revcounter` over two rows gives 100% and
        50% whatever the years are, so a 20% track can only have come from
        the data.
        """
        self.assertEqual(
            self._rendered_widths(SKILLS),
            {"Python / Django / FastAPI": "100", "AI / LLM Platforms": "20"},
        )

    def test_reordering_the_list_moves_no_bar(self, *_mock):
        """The defect this story exists to kill: order must not be a statistic."""
        self.assertEqual(
            self._rendered_widths(SKILLS),
            self._rendered_widths(list(reversed(SKILLS))),
        )

    @patch("ui.views.fetch_skills", return_value=SKILLS)
    def test_only_the_primary_focus_carries_the_marker(self, *_mocks):
        """One skill is flagged, so exactly one marker is drawn -- on that row."""
        response = self.client.get(reverse("ui:home"))

        self.assertContains(response, "◀ PRIMARY", count=1)
        self.assertRegex(
            response.content.decode(), r"(?s)AI / LLM Platforms.*?◀ PRIMARY"
        )

    def test_zero_years_renders_a_zero_and_an_empty_track(self, *_mock):
        """`0` is a stored value, so it prints -- and draws nothing."""
        skills = [
            {"id": 1, "name": "Rust", "years": 0, "is_primary_focus": False},
            {"id": 2, "name": "Go", "years": 4, "is_primary_focus": False},
        ]
        with patch("ui.views.fetch_skills", return_value=skills):
            response = self.client.get(reverse("ui:home"))

        self.assertContains(response, "0 YRS")
        self.assertEqual(self._rendered_widths(skills), {"Rust": "0", "Go": "100"})
        self.assertContains(response, "width:0%")

    def test_an_all_zero_panel_renders_empty_tracks(self, *_mock):
        """The database state between US-2.2-BE's defaults and US-2.5-BE's seed.

        The scale is zero here, so the percentage is never computed. The bar
        it would have produced is not a short one: `.xp-fill` declares no
        width of its own, so `width:` or `width:%` renders FULL -- a brand new
        invented statistic standing exactly where the old one was removed.
        """
        skills = [
            {"id": 1, "name": "Rust", "years": 0, "is_primary_focus": False},
            {"id": 2, "name": "Go", "years": 0, "is_primary_focus": False},
        ]
        with patch("ui.views.fetch_skills", return_value=skills):
            response = self.client.get(reverse("ui:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "width:0%", count=2)
        self.assertNotContains(response, "width:%")
        self.assertNotContains(response, 'width:"')

    @patch("ui.views.fetch_skills", return_value=LEGACY_SKILLS)
    def test_a_backend_without_the_fields_still_renders(self, *_mocks):
        """The frontend is a separate service and cannot assume the API's version."""
        response = self.client.get(reverse("ui:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django / Python / FastApi")
        self.assertNotContains(response, "YRS")
        self.assertNotContains(response, "◀ PRIMARY")
        self.assertContains(response, "width:0%")


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

    @patch("ui.views.fetch_skills", return_value=SKILLS)
    @patch("ui.views.fetch_projects", side_effect=PortfolioNotFoundError("gone"))
    def test_a_list_404_still_renders_signal_lost(self, *_mocks):
        """A 404 on the LIST route is an outage, not a missing project.

        If `/api/projects/` itself 404s the API is misconfigured or gone, so
        the honest panel is still SIGNAL LOST. The narrow type exists for a
        detail route that is not written yet; until a view opts in by catching
        it, the page must not change. What this pins is that `_safe` catches
        the subclass through its parent arm, so what a visitor is shown is
        still the panel an outage draws.
        """
        response = self.client.get(reverse("ui:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SIGNAL LOST")


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
