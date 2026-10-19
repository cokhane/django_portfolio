"""Tests for the first-visit world chooser.

A separate module for the reason `test_theme.py`, `test_hire_me_panel.py` and
`test_preferences.py` each record: `tests.py` is already over 800 lines against
pylint's `too-many-lines` ceiling of 1000. The story's Scope names `tests.py`
because it was written before that split; the split is the newer decision and
the one the repo follows.

**Django renders templates; it does not run them.** So nothing here proves the
chooser WORKS -- not that it opens, not that Escape persists, not that Tab
stays inside it. Those are in the story's Verification block and were done by
hand. What a render genuinely carries is pinned here instead, and the first of
them is the one that matters most:

1. **The dialog ships `hidden`.** This is the load-bearing assertion of the
   story. Markup that shipped visible and was hidden by script would hand a
   visitor with JavaScript off a modal over every page of the site with no way
   to dismiss it -- the locked door **F-13** describes and a breach of **A1**.
   It is one attribute, it is invisible in every other test, and getting it
   backwards is silent.
2. **The chooser touches no storage.** US-5.3 owns NFR-7's guards; a second
   script reaching `localStorage` directly would be a second place to get a
   private window wrong.
3. **The swatches still mirror the palettes.** The mockup's literals are
   copied into the stylesheet rather than reached through `var()`, so nothing
   but a test keeps them honest when a world is retuned.
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import ROOT_CLASSES, THEME_PARAM
from .test_preferences import _inline_script, _render_every_page, _without_scripts
from .test_theme import _declaration_block, _stylesheet, _without_comments
from .tests import AVAILABILITY, PROJECTS, SKILLS

# Each world's display name, frozen by F-18: a world changes the palette,
# never the words, so these are the mockup's strings and a story that wanted
# to reword one would be changing content, which US-5.4 puts out of scope.
#
# Mapped to the world rather than listed, because the assertion that matters
# is that THIS card says THIS name. Asserting the four strings appear "on the
# page" proves nothing at all: every one of them already appears in a comment
# in `base.html`, and comments in that file render into every response --
# "Arcade" eleven times. A card could lose its name entirely and a page-wide
# search would still find it.
WORLD_NAMES = {
    "clean": "Just the Work",
    "manor": "Haunted Manor",
    "horror": "Found Footage",
    "arcade": "Arcade",
}

# One card: the world it offers, and the markup between its `data-pick` and
# its closing tag. Anchored on the attribute rather than on the opening tag's
# full text so re-ordering attributes cannot fail a test about the content.
CARD = re.compile(r'data-pick="([a-z]+)">(.*?)</button>', re.S)

# What tells the chooser's script apart from the store's: it is the one that
# builds the grid. `test_preferences.py` anchors on `window.axePrefs =` for
# the same reason in reverse -- the two are told apart by what they do with
# the API, not by their order in the document.
CHOOSER_MARKER = "ch-grid"

# `<button ... data-pick="name">`, the four cards.
PICK = re.compile(r'data-pick="([a-z]+)"')

# A swatch rule as the stylesheet spells it: `.sw-<world>-<n>{background:#hex}`.
SWATCH = re.compile(r"\.sw-([a-z]+)-\d\{background:(#[0-9a-f]{6})\}")

# Any `--token:#hex` declaration, for reading a world's palette back out.
TOKEN_VALUE = re.compile(r"--[a-z-]+\s*:\s*(#[0-9a-f]{6})")


def _palette_selector(world):
    """Where `world`'s tokens are declared.

    Derived from `ROOT_CLASSES` rather than written out, for the reason this
    module's own `test_all_four_worlds_are_offered` gives: a hand-written list
    can only ever check itself. Arcade's class is the empty string because
    Arcade IS `:root`, and that is exactly the case a typed-out list gets
    wrong.
    """
    return f".{ROOT_CLASSES[world]}" if ROOT_CLASSES[world] else ":root"


def _open_tag(html, element_id):
    """The opening tag that carries `id="<element_id>"`.

    Anchored on the id rather than on a line number or an attribute order, so
    re-wrapping the markup cannot fail a test that is really about whether one
    attribute is present.
    """
    start = html.index(f'id="{element_id}"')
    return html[html.rindex("<", 0, start):html.index(">", start) + 1]


def _chooser_script(html):
    """The chooser's script source, which must be exactly one element."""
    return _inline_script(html, CHOOSER_MARKER)


def _css(html):
    """The stylesheet as the slicing helpers need it: no commentary.

    `test_theme.py` owns both halves and records why the strip comes first --
    a slice looks for a selector followed by an opening brace, and prose in
    this stylesheet that quotes one is found before the rule itself.
    """
    return _without_comments(_stylesheet(html))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ChooserMarkupTests(SimpleTestCase):
    """What the server actually sends, on every page a visitor can reach."""

    def _home(self, query=None):
        """The home page's HTML, optionally pinned to a world."""
        return self.client.get(reverse("ui:home"), query or {}).content.decode()

    def _pages(self):
        """The three renders of `base.html`, from the shared helper."""
        return _render_every_page(self.client)

    def test_the_chooser_ships_hidden_on_every_page(self, *_mocks):
        """AC 5, and the assertion this story exists to protect (A1, F-13).

        `hidden` has to be in the bytes the server sends, not applied by the
        script afterwards. The difference is invisible to anyone with
        JavaScript on and total to anyone without it: the other way round,
        every page of the site carries an opaque dialog that nothing will
        ever close.

        Asserted per page because `base.html` has three renderers and one of
        them is not ours -- Django's own `page_not_found`. A mechanism wired
        into a view would be absent exactly there.
        """
        for name, html in self._pages().items():
            with self.subTest(page=name):
                self.assertIn(" hidden>", _open_tag(html, "chooser"))

    def test_the_re_open_control_ships_hidden_on_every_page(self, *_mocks):
        """AC 11: the way back exists, and it is not a dead control.

        It only works with JavaScript, so it is revealed by JavaScript -- the
        same contract the dialog has. A button rendered visible that does
        nothing when pressed is worse than no button.
        """
        for name, html in self._pages().items():
            with self.subTest(page=name):
                self.assertIn(" hidden>", _open_tag(html, "site-controls"))
                self.assertIn('id="open-chooser"', html)

    def test_all_four_worlds_are_offered(self, *_mocks):
        """AC 7: four cards, one per world, and the set comes from Python.

        Derived from `ROOT_CLASSES` rather than typed out, because a
        hand-written list can only ever check itself: add a fifth world
        tomorrow and a list-driven test passes while the chooser silently
        stops offering it.

        Order-independent, and deliberately so. The cards run Just the Work,
        Haunted Manor, Found Footage, Arcade -- the mockup's order, which is
        a design decision about what to show a client first and is not
        `ROOT_CLASSES`'s business. `assertCountEqual` still catches a missing
        world, an extra one and a duplicate.
        """
        self.assertCountEqual(PICK.findall(self._home()), list(ROOT_CLASSES))

    def test_each_card_names_its_world(self, *_mocks):
        """AC 7: the card says which world it is, in the mockup's words (F-18).

        Asserted INSIDE each card, keyed to the world it offers. The obvious
        version of this test -- four names, `assertIn` against the page --
        cannot fail: `base.html` names all four worlds in its comments, and
        comments in that file render into every response. A card stripped of
        its name would still have passed it.
        """
        cards = dict(CARD.findall(self._home()))

        self.assertEqual(set(cards), set(WORLD_NAMES))
        for world, name in WORLD_NAMES.items():
            with self.subTest(world=world):
                self.assertIn(f">{name}</span>", cards[world])

    def test_the_chooser_is_one_step(self, *_mocks):
        """AC 7 (F11): four cards and a skip, and nothing else to answer.

        F11 is explicit that a second step ends the justification for showing
        an interstitial between a client and the work at all. The effects and
        scares switches belong to US-5.5 and US-5.6 and are not chooser
        steps; this fails if one is ever added inside the dialog.

        Bounded by the two ids rather than by the whitespace between the two
        elements, which is the rule `_open_tag` states and this test used to
        break: an anchor on `</div>\\n\\n<div` makes re-indenting the
        template fail a test about how many questions a visitor is asked.
        """
        html = self._home()
        dialog = html[html.index('id="chooser"'):html.index('id="site-controls"')]

        self.assertEqual(dialog.count("<button"), len(ROOT_CLASSES) + 1)
        self.assertIn('id="ch-skip"', dialog)

    def test_the_dialog_is_labelled_and_modal(self, *_mocks):
        """F-14: a dialog a screen reader can announce and name."""
        tag = _open_tag(self._home(), "chooser")

        self.assertIn('role="dialog"', tag)
        self.assertIn('aria-modal="true"', tag)
        self.assertIn('aria-labelledby="ch-title"', tag)

    def test_the_chooser_renders_identically_in_every_world(self, *_mocks):
        """F-18, for this story's own markup.

        The dialog carries no server-rendered world name, and this is what
        says so. An earlier draft put the active world in a `data-` attribute
        so Escape could persist it; that made the chooser the second thing in
        the document that differs between two worlds, which is exactly what
        `test_theme.py`'s identical-documents assertion forbids. The script
        reads the applied world off `<html>` instead.
        """
        clean = self._home({THEME_PARAM: "clean"})
        horror = self._home({THEME_PARAM: "horror"})

        self.assertEqual(_open_tag(clean, "chooser"), _open_tag(horror, "chooser"))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ChooserScriptTests(SimpleTestCase):
    """The second script's shape -- the half a template render can see."""

    def _home(self):
        """The home page's HTML."""
        return self.client.get(reverse("ui:home")).content.decode()

    def test_the_chooser_never_touches_storage(self, *_mocks):
        """NFR-7 stays owned by one script.

        US-5.3 put every `localStorage` access behind a `try` in one place
        and `test_preferences.py` counts them. A second script reaching
        storage directly would be a second place to get a private window
        wrong, and the count there would no longer mean what it says.
        """
        self.assertNotIn("localStorage", _chooser_script(self._home()))

    def test_the_chooser_writes_only_through_the_store(self, *_mocks):
        """AC 2: one write path, and it is the one that validates.

        `setWorld` is the single validation point US-5.3 built. A chooser
        that applied a class itself would be a second way to put a world on
        the page, free to disagree with the stored value.
        """
        script = _chooser_script(self._home())

        self.assertIn("window.axePrefs.setWorld(name)", script)
        self.assertNotIn("classList.add", script)

    def test_the_chooser_never_logs(self, *_mocks):
        """The store's rule, extended: a visitor's console is not a notepad."""
        self.assertNotIn("console.", _chooser_script(self._home()))

    def test_closing_is_hidden_and_never_opacity(self, *_mocks):
        """AC 9 (NFR-8): a closed chooser intercepts nothing.

        Two halves, because the rule fails two ways. The script closes by
        setting `hidden`, never by fading the element out -- an element at
        `opacity: 0` still covers the page and still takes every click. And
        the stylesheet restates `[hidden]{display:none}`, because `.chooser`
        is `display:flex` and that outranks the UA stylesheet's rule for the
        attribute. Without the restatement, setting `hidden` would close
        nothing at all.
        """
        html = self._home()

        self.assertIn("chooser.hidden = true", _chooser_script(html))
        self.assertNotIn("opacity", _chooser_script(html))
        self.assertIn(".chooser[hidden]{display:none}", _css(html))

    def test_the_skip_picks_from_the_rendered_vocabulary(self, *_mocks):
        """S12: a skip that picks at random, from the names Python knows.

        The randomness itself cannot be tested here -- Django does not run
        the script, and it was checked by hand instead. What is pinned is
        that the pool is the rendered vocabulary, so "surprise me" can never
        offer a world the server does not recognise.
        """
        script = _chooser_script(self._home())

        self.assertIn("names[Math.floor(Math.random() * names.length)]", script)
        self.assertIn('document.getElementById("theme-worlds")', script)

    def test_a_pinned_render_does_not_ask(self, *_mocks):
        """The `?theme=` QA override survives this story.

        A tester who asked for a world must not be interrupted by the
        chooser, and must not have their own stored preference overwritten
        by looking at someone else's. The server already says whether the
        URL pinned the render; the script's open condition obeys it.
        """
        script = _chooser_script(self._home())

        self.assertIn("!pinned && window.axePrefs.world() === null", script)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ChooserPaletteTests(SimpleTestCase):
    """The swatches are a picture of the palettes, so they have to still be one."""

    def _css(self):
        """The stylesheet as rendered on the home page, commentary removed."""
        return _css(self.client.get(reverse("ui:home")).content.decode())

    def test_every_swatch_is_a_colour_its_world_actually_uses(self, *_mocks):
        """The guard that lets the swatches stay literals.

        They cannot be `var()`: reaching another world's tokens from here
        would mean putting that world's class on the element, which imports
        every one of its descendant rules along with the twelve properties
        wanted. So the mockup's hexes are copied -- and a copy with nothing
        checking it is a copy that drifts. Retune a world and its swatch
        silently advertises a colour the site no longer uses anywhere.

        Asserted as membership rather than slot by slot: which token a swatch
        shows is the mockup's design decision, not this test's business. That
        it is one of that world's colours at all is.

        Membership is the exact strength, measured rather than assumed. Move
        Manor's `--gold` alone and this stays green, because Manor's `--gold`
        and `--ember` coincide and the value is still one Manor uses -- which
        is the contract working, not a hole in it. Move the value out of the
        world entirely and it goes red, naming the world and the orphaned
        hex. That is the drift that matters: a swatch advertising a colour
        the site no longer paints anything with.
        """
        css = self._css()
        palettes = {
            world: set(TOKEN_VALUE.findall(_declaration_block(css, _palette_selector(world))))
            for world in ROOT_CLASSES
        }

        swatches = SWATCH.findall(css)
        self.assertEqual(len(swatches), len(ROOT_CLASSES) * 4, "expected four swatches per world")
        for world, value in swatches:
            with self.subTest(world=world, value=value):
                self.assertIn(value, palettes[world])

    def test_the_chooser_scrolls_rather_than_clipping(self, *_mocks):
        """AC 10 (F-13): the 320px gate, pinned as far as text can pin it.

        Layout needs a browser, so the by-hand check is the real gate. What a
        text assertion can hold is the specific mistake: `align-items:center`
        on a scrolling flex container strands content past the start edge
        where no scroll reaches it. `margin:auto` centres the same way
        without that. This fails if someone reinstates the mockup's version.
        """
        css = self._css()

        chooser = _declaration_block(css, ".chooser")
        self.assertIn("overflow-y:auto", chooser)
        self.assertIn("overscroll-behavior:contain", chooser)
        self.assertNotIn("align-items", chooser)
        # Bounded to the rule, like the three above it. An unbounded slice to
        # the end of the stylesheet would be silenced by any later
        # `margin:auto` and would stop constraining this rule at all.
        self.assertIn("margin:auto", _declaration_block(css, ".chooser-inner"))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ChooserWithoutJavaScriptTests(SimpleTestCase):
    """AC 6 (A1): with JavaScript off there is no modal, and no dead control.

    `test_preferences.py` already proves the portfolio reads without script.
    This is the half US-5.4 adds: the markup this story puts on every page
    must not become an obstacle for the visitor who cannot run it.
    """

    def _stripped_home(self):
        """The home page as a visitor with JavaScript disabled receives it."""
        return _without_scripts(self.client.get(reverse("ui:home")).content.decode())

    def test_no_modal_reaches_a_visitor_without_script(self, *_mocks):
        """The dialog is inert markup, because only script ever reveals it."""
        html = self._stripped_home()

        self.assertIn(" hidden>", _open_tag(html, "chooser"))
        self.assertIn(" hidden>", _open_tag(html, "site-controls"))

    def test_the_work_is_still_reachable_without_script(self, *_mocks):
        """The chooser added markup to every page; the page still works.

        `test_preferences.py` pins this for the store. Repeated here because
        the thing being guarded changed: a full-viewport `position:fixed`
        overlay is exactly the kind of addition that takes a site away from
        a visitor who cannot dismiss it, and it now ships on every page.
        """
        html = self._stripped_home()

        for project in PROJECTS:
            with self.subTest(project=project["slug"]):
                self.assertIn(project["title"], html)
