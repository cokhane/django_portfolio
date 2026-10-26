"""US-7.3 — the keyboard and screen-reader audit, kept closed.

A separate module from `tests.py` for the two reasons `test_theme.py` l.3-7
records, both of which still hold: `tests.py` is 843 lines against pylint's
`too-many-lines` ceiling of 1000, and the story names `tests.py` only because
it was written before that split. A third reason applies here — thirteen
modules import fixtures `from .tests`, so `tests.py` cannot import their
helpers back, and every assertion below wants one: `_render_every_page`
(the three renderers of `base.html`, one of them Django's own
`page_not_found`), `_element`, `_open_tag` and `test_theme.py`'s slicers.

What this module is NOT. It is not a second copy of
`test_decor.py::test_nothing_in_the_layer_can_take_a_click_or_a_focus`, which
is already the story's "nothing focusable in the decoration layer" and is left
untouched. What it adds beside it is the SVG-level guard — the one element
type that can enter the tab order while its container is correctly fenced.

**These tests assert STRUCTURE, which is the half a Django suite can see.** No
suite can see a painted focus ring; what it can see is that the rule painting
it still exists and is not taken back. The ring contrasts themselves were
measured in a real browser, before and after, in `docs/evidence/US-7.3/`.
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .test_chooser import _css, _open_tag
from .test_decor import _element
from .test_effects import LAYER_ID
from .test_preferences import _render_every_page
from .test_theme import _declaration_block
from .tests import AVAILABILITY, PROJECTS, SKILLS

SKIP_CLASS = "skip-link"
MAIN_ID = "main"
GRID_ID = "grid"

# The site's one focus ring, shared by this module and `test_side_quest.py` so
# the selector has a single definition. `base.html`'s own comment above the
# rule is the authority on why the selector carries a `body ` prefix.
SITE_WIDE_RING = "body :focus-visible"
RING_DECLARATION = "outline:2px solid var(--ember)"
HORROR_RING = ".horror :focus-visible"

# The base rule, spelled exactly. Looked up as a whole selector list so the
# test pins THAT rule rather than any rule whose text happens to contain the
# class -- `.manor .btn.btn-primary` would satisfy a bare substring search.
PRIMARY_BASE_RULE = '.btn[aria-pressed="true"],.btn.btn-primary'

# Every `<svg` opening tag, so the guard counts TAGS and not occurrences of
# the word: a partial included twice renders twice from one tag.
SVG_OPEN = re.compile(r"<svg\b[^>]*>")

# `aria-pressed` is a toggle-BUTTON state; on a link it is invalid ARIA.
# Matched over `<a ` opening tags only, so the buttons that carry it
# legitimately are not swept up.
LINK_OPEN = re.compile(r"<a\b[^>]*>")

# `<main` carrying the skip link's target, as ONE tag. Asserting the id and
# the element separately would pass with `id="main"` on any stray `<div>`.
MAIN_TAG = re.compile(rf'<main\b[^>]*id="{MAIN_ID}"')

# A `.btn-primary` NOT preceded by `.btn` -- the `BorderColourAsTextTests`
# lookbehind idiom. The hook must always be written `.btn.btn-primary`, and
# this finds every way of writing it that is not, wherever in a selector list
# it appears.
BARE_PRIMARY = re.compile(r"(?<!\.btn)\.btn-primary")

# Everything the HTML spec makes focusable without a `tabindex`, plus the
# attribute itself. The skip link has to come before all of them, and a list
# that stopped at `<a` and `<button` would miss the day someone adds a form.
FOCUSABLE_MARKUP = ("<a ", "<button", "<input", "<select", "<textarea", "<summary", "tabindex=")


def _home_sheet(client):
    """`base.html`'s inline stylesheet, as the home page renders it."""
    return _css(client.get(reverse("ui:home")).content.decode())


@patch("ui.views.fetch_projects", return_value=PROJECTS)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
class SkipLinkTests(SimpleTestCase):
    """AC 5: a skip link that reaches main content and shows itself on focus.

    The link lives in `base.html`, so it is on all three pages; `#main` is on
    all three too, which is the half that makes one link enough.
    """

    def _body(self, html):
        """Everything from `<body>` on, which is where tab order starts."""
        return html[html.index("<body>"):]

    def test_the_skip_link_is_the_first_focusable_thing_on_every_page(self, *_mocks):
        """First in `<body>`, because a skip link reached second skips nothing.

        Asserted as a POSITION rather than as presence: the defect this guards
        is someone adding a control above it, which leaves the markup looking
        correct while the link quietly stops being reachable first.

        Written as one comparison against the EARLIEST focusable thing on the
        page, not as a loop of per-pattern checks -- the question is simply
        whether anything focusable precedes the link, and the earliest match
        answers it for the whole set at once.
        """
        for name, html in _render_every_page(self.client).items():
            body = self._body(html)
            skip = body.index(SKIP_CLASS)
            found = [body.index(mark) for mark in FOCUSABLE_MARKUP if mark in body]
            with self.subTest(page=name):
                self.assertTrue(found, f"nothing focusable found on {name} at all")
                # The skip link is itself an `<a `, so the earliest focusable
                # markup must be the one that opens it.
                self.assertEqual(min(found), body.rindex("<a ", 0, skip))

    def test_the_skip_link_points_at_a_target_that_exists_on_every_page(self, *_mocks):
        """A skip link whose href resolves to nothing is worse than none.

        It reports success to the visitor -- focus appears to move -- and
        leaves them where they were. The id and the element are matched as ONE
        tag: `id="main"` on some other element would satisfy both halves
        separately while the landmark it is supposed to name went missing.
        """
        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                self.assertIn(f'href="#{MAIN_ID}"', html)
                self.assertRegex(html, MAIN_TAG)

    def test_the_skip_link_is_hidden_by_clipping_and_not_by_removal(self, *_mocks):
        """`display:none` and `visibility:hidden` take it OUT of the tab order.

        That is the one way of getting this wrong that still looks right in
        the markup: the link is there, it is styled, and no keyboard can ever
        reach it.
        """
        hidden = _declaration_block(_home_sheet(self.client), f".{SKIP_CLASS}:not(:focus)")

        self.assertIn("clip-path", hidden)
        self.assertNotIn("display:none", hidden)
        self.assertNotIn("visibility:hidden", hidden)


@patch("ui.views.fetch_projects", return_value=PROJECTS)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
class LiveRegionTests(SimpleTestCase):
    """AC 4: the category swap has to announce itself.

    Before this story the page carried no live region at all, while the one
    dynamic interaction the site has replaced the whole grid.
    """

    def test_the_grid_announces_what_the_swap_put_in_it(self, *_mocks):
        """On `#grid` itself, which is the element HTMX keeps."""
        tag = _open_tag(self.client.get(reverse("ui:home")).content.decode(), GRID_ID)

        self.assertIn('aria-live="polite"', tag)

    def test_the_swapped_fragment_declares_no_region_of_its_own(self, *_mocks):
        """The region must live on the container, not in what replaces it.

        `hx-swap="innerHTML"` destroys and rebuilds the children on every
        swap, so a region declared in the fragment is a NEW region each time --
        and a region that did not exist before the change reads as initial
        content and announces nothing. This is the subtle half of AC 4 and the
        reason the attribute is where it is.
        """
        fragment = self.client.get(reverse("ui:project-grid")).content.decode()

        self.assertNotIn("aria-live", fragment)
        self.assertNotIn('role="status"', fragment)


@patch("ui.views.fetch_projects", return_value=PROJECTS)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
class DecorationFocusabilityTests(SimpleTestCase):
    """AC 3 (**NFR-8**), the SVG half.

    `test_decor.py::test_nothing_in_the_layer_can_take_a_click_or_a_focus`
    already fences the layer against `tabindex` and focusable elements. This
    is the one element type that walks through that fence: in some browsers an
    `<svg>` is focusable by DEFAULT, with no `tabindex` to find and nothing in
    the markup to see, and `aria-hidden` on an ancestor does not remove it
    from the tab order.
    """

    def test_every_svg_in_the_layer_is_kept_out_of_the_tab_order(self, *_mocks):
        """Over the rendered layer, so a new partial is covered the day it lands."""
        for name, html in _render_every_page(self.client).items():
            tags = SVG_OPEN.findall(_element(html, LAYER_ID))
            with self.subTest(page=name):
                self.assertTrue(tags, f"no <svg> found in #{LAYER_ID} on {name}")
                self.assertEqual(
                    [tag for tag in tags if 'focusable="false"' not in tag],
                    [],
                    "a decorative <svg> can take focus in browsers that make "
                    "SVG focusable by default; aria-hidden does not stop it",
                )


@patch("ui.views.fetch_projects", return_value=PROJECTS)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
class FocusRingTests(SimpleTestCase):
    """AC 2: a ring that is visible in all four worlds.

    The suite cannot see a painted ring. What it can see is that the rule
    painting it is still there, still reads a token rather than a literal, and
    is not taken back -- which is every way the measured ring could silently
    stop being one. The measurements are in `docs/evidence/US-7.3/`.
    """

    def test_the_ring_is_authored_once_for_the_whole_site(self, *_mocks):
        """One rule, reading a token every world defines.

        Promoted from the two elements that used to carry their own copy of
        the same declaration. `base.html`'s comment above the rule is the
        authority on the selector's `body ` prefix; this pins that the rule
        exists, carries an offset, and is still the only one of its kind.
        """
        sheet = _home_sheet(self.client)
        block = _declaration_block(sheet, SITE_WIDE_RING)

        self.assertIn(RING_DECLARATION, block)
        self.assertIn("outline-offset", block)
        # "Once" in the test's name, asserted: the two collapsed rules must
        # not come back alongside it.
        self.assertNotIn(".ch-card:focus-visible", sheet)
        self.assertNotIn("#sk-canvas:focus-visible", sheet)

    def test_found_footage_overrides_the_ring_with_its_legible_accent(self, *_mocks):
        """The one world where the shared token is not enough.

        `--lit` is the token US-7.1 added for exactly this problem in exactly
        this world; the ratios are recorded beside its definition in
        `base.html` and in the evidence file. Only the colour is overridden.
        """
        self.assertIn("var(--lit)", _declaration_block(_home_sheet(self.client), HORROR_RING))

    def test_nothing_in_the_stylesheet_takes_the_ring_back(self, *_mocks):
        """`outline:none` is how a focus ring disappears unnoticed.

        The mockup set it, US-5.4's CORRECTION 3 dropped it, and a reflowed
        copy-paste is all it would take to bring it back -- invisibly, because
        the rule that paints the ring would still be sitting right there.
        """
        sheet = _home_sheet(self.client)

        for taken_back in ("outline:none", "outline: none", "outline:0"):
            with self.subTest(declaration=taken_back):
                self.assertNotIn(taken_back, sheet)


@patch("ui.views.fetch_projects", return_value=PROJECTS)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
class HeadingAndStateTests(SimpleTestCase):
    """AC 6 and the audit's critical finding.

    Heading ORDER was measured gapless and needs no guard. What needed fixing
    was a page with no `h1` at all, and a link wearing a button's state.
    """

    def test_every_page_has_exactly_one_level_one_heading(self, *_mocks):
        """The 404 had none: its title was a `<p>`, and its only heading was
        the chooser's hidden `h2`, so listing headings there returned nothing.
        """
        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                self.assertEqual(html.count("<h1"), 1, f"{name} needs exactly one <h1>")

    def test_no_link_wears_a_toggle_buttons_pressed_state(self, *_mocks):
        """`aria-pressed` on an `<a>` is invalid ARIA -- axe reports it critical.

        It was on the hero CTA to borrow the fill that
        `.btn[aria-pressed="true"]` paints in all four worlds: a false state
        used as a styling hook, which told a screen reader the link was a
        pressed toggle. `.btn-primary` is that hook now. The genuine buttons
        are untouched -- the match is over `<a` opening tags only.
        """
        for name, html in _render_every_page(self.client).items():
            offenders = [tag for tag in LINK_OPEN.findall(html) if "aria-pressed" in tag]
            with self.subTest(page=name):
                self.assertEqual(
                    offenders,
                    [],
                    "aria-pressed is a button state; use .btn-primary for the "
                    f"styling. Offending tags: {offenders}",
                )

    def test_the_primary_hook_cannot_be_outranked_by_hover(self, *_mocks):
        """`.btn.btn-primary`, never a bare `.btn-primary`.

        Measured: with the bare class the hero button keeps its fill at rest
        in all four worlds and loses it the moment a pointer touches it, in
        all four -- `.btn:hover` is (0,2,0) and a bare `.btn-primary` (0,1,0).
        In Arcade that painted gold text on a gold fill.

        Both halves matter and neither alone is enough. The base rule is
        pinned as a whole selector list, because a substring search for the
        class is satisfied by any world's copy; the lookbehind then catches a
        bare spelling ANYWHERE, including the orderings a fixed-string search
        would walk straight past.
        """
        sheet = _home_sheet(self.client)

        self.assertIn("background:var(--gold)", _declaration_block(sheet, PRIMARY_BASE_RULE))
        self.assertEqual(
            BARE_PRIMARY.findall(sheet),
            [],
            ".btn-primary must always be written .btn.btn-primary, or "
            ".btn:hover outranks it and the hero button loses its fill on hover",
        )
