"""Tests for the hire-me panel, the home page's conversion step.

Split out of `tests.py` rather than added to it: that module had reached
1032 lines covering the API client, four views and their degradation
paths, and pylint's `too-many-lines` is right that it had stopped being one
subject. This module is the panel US-4.2 built -- the availability
statement, the engagement cards and the contact route -- plus US-4.3's CV
download, which landed beside the mailto rather than in the nav. US-4.4's
contact-route decision lands here too. The shared payload fixtures stay in
`tests.py` next to `PROJECTS` and `SKILLS`, imported here, so there is still
exactly one definition of each.
"""

from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import SimpleTestCase
from django.urls import reverse

from .api import PortfolioAPIError
from .tests import (
    AVAILABILITY,
    CONTACT_HREF,
    CV_DOWNLOAD_NAME,
    CV_STATIC_PATH,
    EMPTY_AVAILABILITY,
    ENGAGEMENTS,
    NEXT_MONTH,
    PITCH_LINE,
    PROJECTS,
    SKILLS,
)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class HireMePanelTests(SimpleTestCase):
    """The panel that turns a persuaded reader into an email.

    Three things are pinned here that nothing else can pin. First, the
    availability state is conveyed by a WORD and not only by a coloured dot,
    because a screen reader and a colour-blind client both get nothing from
    the dot (BRD F-14). Second, the availability data is ONE payload -- the
    state, the month and the cards all arrive from `/api/availability/` and
    all degrade together -- while the pitch line and the contact route are
    template copy that must survive the endpoint being down. Third, the two
    ways the from-line could lie: a month that has already passed, and a
    mistyped date that must not take the contact section down with it.
    """

    def _panel(self, response):
        """The rendered contact section, sliced out of the page.

        Panel-scoped assertions have to be panel-scoped to mean anything: a
        bare `assertNotContains(response, "$")` would be answered by any
        project summary quoting a cost, and a bare "contains OPEN" by the word
        appearing anywhere above. `// CONTACT` is the section heading and the
        only place that exact string occurs -- the nav and hero links read
        `CONTACT` without the slashes. This follows
        `SkillsPanelTests._rendered_widths`, which slices for the same reason.
        """
        return response.content.decode().split("// CONTACT")[1]

    def test_renders_the_state_word_the_month_and_the_cards(self, *_mocks):
        """AC 1 and AC 2: every part of a fully configured panel reaches the page.

        The state is asserted as the WORD `OPEN`, which is the whole point of
        AC 2 -- the mockup conveys it with a coloured dot, and colour alone is
        not an indicator. `ARCHITECTURE` is safe to assert even though the
        hero reads `ARCHITECT`, because the longer string cannot be satisfied
        by the shorter one. `CLOUD &amp; DELIVERY` is asserted in its escaped
        form so the test meets Django's autoescaping honestly rather than by
        picking a label that dodges it.
        """
        response = self.client.get(reverse("ui:home"))
        panel = self._panel(response)

        self.assertEqual(response.status_code, 200)
        self.assertIn("PLAYER 2 SLOT: OPEN", panel)
        self.assertIn(f"AVAILABLE FROM {NEXT_MONTH.strftime('%B').upper()}", panel)
        self.assertIn("ARCHITECTURE", panel)
        self.assertIn("AI PLATFORMS", panel)
        self.assertIn("CLOUD &amp; DELIVERY", panel)
        self.assertIn("Grounded retrieval", panel)
        self.assertIn(PITCH_LINE, panel)

    def test_booked_renders_the_word_booked(self, *_mocks):
        """The negative half of AC 2, without which test 1 proves little.

        A template that printed `OPEN` unconditionally -- the easiest way to
        get the first test passing -- would tell every visitor the author is
        free while the database says otherwise. That is worse than no line at
        all, so the other stated word gets its own assertion.
        """
        booked = {**AVAILABILITY, "state": "booked"}
        with patch("ui.views.fetch_availability", return_value=booked):
            panel = self._panel(self.client.get(reverse("ui:home")))

        self.assertIn("PLAYER 2 SLOT: BOOKED", panel)
        self.assertNotIn("SLOT: OPEN", panel)

    def test_an_availability_outage_degrades_only_the_availability_data(self, *_mocks):
        """AC 3, the story's central requirement, in the shape US-4.1 handed over.

        Two independent things are asserted because two independent things
        can break. The panel keeps its pitch line and its `mailto:` -- a
        client must still be able to write the email when the singleton is
        unreachable. And `api_online` stays True: it is read from the projects
        call alone, so a view that set it from any fetch that failed would
        light the `API OFFLINE` badge and swap the grid for `SIGNAL LOST`,
        reporting the whole site as down over the one endpoint whose absence
        the page is built to absorb. This is
        `test_a_skills_outage_still_renders_the_projects` for a third
        endpoint, plus the badge the other two do not touch.
        """
        with patch("ui.views.fetch_availability", side_effect=PortfolioAPIError("down")):
            response = self.client.get(reverse("ui:home"))
        panel = self._panel(response)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["api_online"])
        self.assertNotIn("PLAYER 2 SLOT", panel)
        self.assertNotIn("AVAILABLE FROM", panel)
        self.assertNotIn("ARCHITECTURE", panel)
        self.assertIn(PITCH_LINE, panel)
        self.assertIn(CONTACT_HREF, panel)
        self.assertContains(response, "E-Commerce Platform")
        self.assertContains(response, "API ONLINE")
        self.assertNotContains(response, "API OFFLINE")
        self.assertNotContains(response, "SIGNAL LOST")

    def test_nothing_configured_still_renders_a_working_panel(self, *_mocks):
        """AC 4: US-4.1 Q2's empty shape is the live site, not an edge case.

        The seed command creates no availability row and no engagements, so
        this payload is what the backend serves on the day this ships. The
        panel therefore has to read as finished with none of its data: no
        `UNSTATED` word rendered where silence is the honest answer, and no
        "no cards yet" placeholder -- unlike CORE SKILLS, the list is not this
        panel's whole content, and a placeholder would be a sentence the
        author cannot edit sitting in the one section that must convert.
        """
        with patch("ui.views.fetch_availability", return_value=EMPTY_AVAILABILITY):
            response = self.client.get(reverse("ui:home"))
        panel = self._panel(response)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("PLAYER 2 SLOT", panel)
        self.assertNotIn("UNSTATED", panel)
        self.assertNotIn("AVAILABLE FROM", panel)
        self.assertNotIn("ARCHITECTURE", panel)
        self.assertIn(PITCH_LINE, panel)
        self.assertIn(CONTACT_HREF, panel)

    def test_an_outage_and_an_empty_statement_draw_the_same_panel(self, *_mocks):
        """A dead endpoint and a silent author are one statement, drawn one way.

        "Nothing has been said about availability" is the honest reading of
        both, and the panel is not the place to distinguish them: the hero
        badge and the grid already report a backend outage, so a notice here
        would be the third time the page says it, in the one section that has
        to stay persuasive. Measured: adding a `availability_down` flag to the
        context and an "availability unavailable" line to the template fails
        this and nothing else in the suite.

        What this does NOT catch -- measured, not assumed -- is a hard-coded
        fallback card. A fallback keyed on an empty `engagements` fires in
        BOTH states, so the two panels stay equal and this test passes. The
        guards against that are
        `test_an_availability_outage_degrades_only_the_availability_data` and
        `test_nothing_configured_still_renders_a_working_panel`, which assert
        no card label survives; both fail on such a fallback. The distinction
        matters because a fallback is the obvious "fix" for AC 3's original
        wording, and US-4.1 made the cards a model precisely so the author's
        own words -- not template text -- are what renders (BRD F-11).
        """
        with patch("ui.views.fetch_availability", side_effect=PortfolioAPIError("down")):
            outage = self._panel(self.client.get(reverse("ui:home")))
        with patch("ui.views.fetch_availability", return_value=EMPTY_AVAILABILITY):
            empty = self._panel(self.client.get(reverse("ui:home")))

        self.assertEqual(outage, empty)

    def test_partial_configuration_renders_each_half_independently(self, *_mocks):
        """A half-finished admin edit shows what exists, not nothing.

        The two halves arrive in one payload but are not one decision: US-4.1
        serves engagement cards whether or not the availability row exists
        (`test_cards_without_a_row_still_serve`), so cards typed before the
        state is set must still render, and a state set before any card is
        typed must still show its tag. Sending both through the same view is
        what makes the independence checkable -- a template with one combined
        guard would pass whichever of these it was shown alone.
        """
        cards_only = {**EMPTY_AVAILABILITY, "engagements": ENGAGEMENTS}
        with patch("ui.views.fetch_availability", return_value=cards_only):
            panel = self._panel(self.client.get(reverse("ui:home")))
        self.assertIn("ARCHITECTURE", panel)
        self.assertNotIn("PLAYER 2 SLOT", panel)

        state_only = {**AVAILABILITY, "engagements": []}
        with patch("ui.views.fetch_availability", return_value=state_only):
            panel = self._panel(self.client.get(reverse("ui:home")))
        self.assertIn("PLAYER 2 SLOT: OPEN", panel)
        self.assertNotIn("ARCHITECTURE", panel)

    def test_a_from_date_that_has_passed_drops_the_line(self, *_mocks):
        """US-4.1 Q3's handed-over behaviour: the stale sign on the door.

        `AVAILABLE FROM NOVEMBER` read the following March is the single
        detail that makes a portfolio look abandoned, and the availability
        line's whole commercial value is proving the opposite. The state tag
        is asserted still present so the fix cannot be "drop the whole tag
        row" -- the author is still open, only the month is no longer news.
        """
        stale = {**AVAILABILITY, "available_from": "2020-11-01"}
        with patch("ui.views.fetch_availability", return_value=stale):
            response = self.client.get(reverse("ui:home"))
        panel = self._panel(response)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("AVAILABLE FROM", panel)
        self.assertIn("PLAYER 2 SLOT: OPEN", panel)

    def test_an_unparseable_from_date_is_dropped_rather_than_a_500(self, *_mocks):
        """A mistyped admin field must not take the contact section down.

        The parse has to happen in the view -- Django's `|date:"F"` formats
        `date` objects and silently renders nothing for a string -- so the
        view is where a bad value would raise. A bare `date.fromisoformat`
        would `ValueError` on this and return a 500 for the one section of
        the site whose entire job is to be reachable. The cards are asserted
        still present: the bad field is one key, and it must not cost the
        panel the rest of its payload.
        """
        typo = {**AVAILABILITY, "available_from": "next month"}
        with patch("ui.views.fetch_availability", return_value=typo):
            response = self.client.get(reverse("ui:home"))
        panel = self._panel(response)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("AVAILABLE FROM", panel)
        self.assertIn("ARCHITECTURE", panel)

    def test_the_send_button_is_the_personal_mailto(self, *_mocks):
        """AC 5, asserted on the ROUTE rather than on the text.

        `PositioningTests.test_contact_uses_the_personal_address` asserts the
        address appears on the page. That would be satisfied by a panel that
        printed the address in prose while the button pointed somewhere else
        -- which is exactly the shape the employer-domain defect had. So this
        asserts the `href`, and that the employer domain is absent from the
        panel.
        """
        panel = self._panel(self.client.get(reverse("ui:home")))

        self.assertIn(CONTACT_HREF, panel)
        self.assertNotIn("anervea.ai", panel)

    def test_no_currency_symbol_appears_on_the_panel(self, *_mocks):
        """AC 6 / BRD G7: rates are on request, so no figure appears here.

        Scoped to the panel rather than the page on purpose: a project summary
        legitimately quotes money ("cut hosting cost 67%"), and a page-wide
        assertion would either fail on that or have to be weakened until it
        proved nothing. G7 is a decision about THIS panel.
        """
        panel = self._panel(self.client.get(reverse("ui:home")))

        for symbol in ("$", "€", "£", "USD", "PHP"):
            self.assertNotIn(symbol, panel)

    def test_the_cv_downloads_from_the_static_path(self, *_mocks):
        """US-4.3 AC 1-3: the link is in the panel, resolved, and saves.

        The expected href is computed with Django's own `static()` rather than
        written as `/static/ui/cv.pdf`, so the assertion follows `STATIC_URL`
        and any future hashing storage instead of pinning today's default and
        failing the day either changes -- the template is what is under test,
        not the staticfiles configuration.

        `download` is asserted because without it the browser navigates to a
        9-page PDF instead of saving it, which is the inline viewer G5 ruled
        out arriving by accident. Its VALUE is asserted too: the attribute
        alone would save the file as `cv.pdf`, anonymous in a downloads folder
        a fortnight later, and naming it is the whole of AC 3.

        Scoped to the panel, like every other assertion here, so a stray CV
        link elsewhere on the page could never satisfy AC 2.
        """
        panel = self._panel(self.client.get(reverse("ui:home")))

        self.assertIn(f'href="{static(CV_STATIC_PATH)}"', panel)
        self.assertIn(f'download="{CV_DOWNLOAD_NAME}"', panel)
        self.assertIn("DOWNLOAD CV", panel)

    def test_the_cv_file_is_discoverable_by_staticfiles(self, *_mocks):
        """AC 4: the file is really there, proved WITHOUT an HTTP status.

        A template test alone passes just as happily when the href points at
        a file nobody committed, so the two have to be pinned together or the
        pair proves only that the markup is self-consistent.

        `finders.find` is a filesystem lookup through the same app-directory
        discovery `{% static %}` describes, so it answers "is the blob where
        the link says" directly. Fetching the URL would NOT answer it: with
        `DEBUG=0` Django serves no static files at all, so the request 404s
        with the file present and correct. AC 4 forbids that assertion for
        exactly this reason -- it would couple the story to the deployment
        question A7 parks, and read red for a reason that is not a defect.
        """
        self.assertIsNotNone(finders.find(CV_STATIC_PATH))
