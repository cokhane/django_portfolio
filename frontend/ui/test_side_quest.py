"""Tests for the skate side quest — the one thing on this site you can play.

A separate module for the reason `test_theme.py`, `test_effects.py`,
`test_decor.py` and `test_lunge.py` each record: `tests.py` is already over
800 lines against pylint's `too-many-lines` ceiling of 1000. The story's Scope
names `tests.py` because it was written before that split; the split is the
newer decision and the one the repo follows.

**Django renders templates; it does not run them.** Nothing here proves the
game is PLAYABLE -- not that a jump clears a cone, not that the score counts
up, not that a wipeout ends the run, and above all not that the loop actually
stopped when a visitor asked for stillness. The story's `## Verification`
block owns all of that and it was run by hand in a real browser; the numbers
are in the story's Implementation notes. What a render genuinely carries is
pinned here, and it is the half that fails SILENTLY -- a missing accessible
name, a tab stop that should not exist, a gate written as a template
condition, a second copy of the palette.

**What this module deliberately does NOT re-assert**, because another module
owns it and two owners is how a contract drifts:

- the `.no-motion` rule count and the absence of an OS-preference media query
  -- `test_effects.py`;
- that `window.axePrefs` is the only thing touching storage -- `test_preferences.py`;
- that two renders of different worlds are byte-identical (**F-18**) --
  `test_theme.py`;
- that nothing inside `#decor` can take a click or a focus -- `test_decor.py`.
  The band is not in `#decor` and could not be; that it is OUTSIDE the layer
  is this module's business and is asserted below.

**AC 11 is the unusual one.** "Functions ≤20 lines, ≤5 args" is a lint rule
in a language this repo has no linter for -- ruff, flake8 and pylint never
read a line of this game. So it is enforced mechanically here instead, by
measuring the rendered source. That is testing shape rather than behaviour,
and it is deliberate: without it the cap is a comment nobody can fail.
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, ROOT_CLASSES, THEME_PARAM
from .test_chooser import _css, _open_tag
from .test_decor import _element
from .test_effects import LAYER_ID
from .test_keyboard import RING_DECLARATION, SITE_WIDE_RING
from .test_lunge import _function_body
from .test_preferences import (
    _assert_work_survives_without_scripts,
    _code_lines,
    _inline_script,
    _render_every_page,
    _without_scripts,
)
from .test_theme import _colour_literals, _declaration_block, _rules_naming
from .tests import AVAILABILITY, PROJECTS, SKILLS

BAND_ID = "side-quest"
CANVAS_ID = "sk-canvas"
GATE_CLASS = "arcade-cast"

# The game script's own marker. Neither of the two scripts in `base.html`
# mentions the canvas, so this finds exactly one block -- which is the whole
# contract `_inline_script` exists to assert, at every call site.
SCRIPT_MARKER = CANVAS_ID

# AC 11, as numbers. Four spaces because this IIFE is nested one level deeper
# than the two in `base.html`: it lives inside `home.html`'s `block content`.
INDENT = "    "
MAX_LINES = 20
MAX_ARGS = 5
DECLARATION = re.compile(rf"^{INDENT}function (\w+)\(([^)]*)\) {{$", re.M)

# A hex triple is the short form and catches the long one too, so one pattern
# finds `#fff` and the `#ff2d55` the mockup hardcodes twelve times.
HEX = re.compile(r"#[0-9a-fA-F]{3}")

# DERIVED from the vocabulary, never typed out. Arcade's root class is the
# empty string, so the band's gate cannot be written as `:not()` the way every
# other cast's is -- it has to name the worlds that HIDE it. That makes it the
# one gate in the stylesheet a fifth world would silently escape, so the
# expectation is built from `ROOT_CLASSES` and a fifth world fails here.
EXPECTED_GATE = ",".join(
    f".{world} .{GATE_CLASS}" for world in ROOT_CLASSES.values() if world
)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class SideQuestMarkupTests(SimpleTestCase):
    """The band: where it is, what it ships as, and what it must not be."""

    def _home(self, query=None):
        """The home page's HTML, optionally pinned to a world."""
        return self.client.get(reverse("ui:home"), query or {}).content.decode()

    def test_the_band_is_on_the_home_page_only(self, *_mocks):
        """The game is the hero's companion; the other two pages never carry it.

        The detail page is the commercial payload -- a client reading
        `// RESULT` is the one moment the site is doing its job -- and the 404
        is someone already lost. Neither is a place to offer a toy, and
        neither has a hero for the band to sit under.

        The ELEMENT is what is absent, not the name: the stylesheet lives in
        `base.html` and so ships on all three pages, which is correct and
        costs two rules nobody renders. A bare search for the id would find
        those and read a stylesheet as a game.
        """
        pages = _render_every_page(self.client)

        self.assertIn(f'id="{CANVAS_ID}"', pages["home"])
        for name in ("detail", "404"):
            with self.subTest(page=name):
                self.assertNotIn(f'id="{CANVAS_ID}"', pages[name])

    def test_the_band_ships_hidden_behind_its_world_gate(self, *_mocks):
        """**A1**: with JavaScript off this must be absent, not dead.

        A 190px strip with an instruction line reading "SPACE jump" under it,
        rendered visible to a visitor whose scripts never run, is a control
        that lies about what it does -- worse than no game at all. The
        `#decor` / `#site-controls` / `.chooser` contract, and the same
        reason: the script that would make it work is the script that reveals
        it.
        """
        tag = _open_tag(self._home(), BAND_ID)

        self.assertIn(" hidden>", tag)
        self.assertIn(GATE_CLASS, tag)

    def test_the_canvas_is_the_one_tab_stop_and_names_itself(self, *_mocks):
        """AC 5, AC 6 and AC 12 -- **F-14**, and **NFR-8**'s one exception.

        Every other thing epic 6 draws is `aria-hidden` with no tab stop. A
        game cannot be played without one, so this is the exception by
        necessity -- which means it has to be exactly ONE, and it has to
        announce itself honestly. A canvas has no readable content inside it,
        so the only decent accessible name says what it is AND that Tab moves
        past it; a reader who cannot be told that is a reader hunting inside
        an empty graphic for content that is not there.

        No `<button>`: the mockup's RESET would be a second tab stop for a
        job Space and a tap already do after a wipeout. No `aria-live` on the
        score: it changes every frame and would turn a reader into a
        metronome.
        """
        band = _element(self._home(), BAND_ID)
        canvas = _open_tag(self._home(), CANVAS_ID)

        self.assertEqual(band.count('tabindex="0"'), 1)
        for forbidden in ("<button", "<a ", "role=", "aria-live"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, band)
        name = re.search(r'aria-label="([^"]+)"', canvas)
        self.assertIsNotNone(name, "the canvas carries no accessible name")
        self.assertIn("Tab", name.group(1))

    def test_the_canvas_declares_no_size_of_its_own(self, *_mocks):
        """One home per dimension: the stylesheet's, read back by the script.

        The mockup spells `width="1100" height="190"` on the element, `190px`
        in its style attribute and `var W = 1100, H = 190` in its script --
        three copies of two numbers, free to disagree the day the band is
        resized. Here the CSS declares the size, the script measures the
        laid-out box, and the attributes are gone. They were only ever a
        pre-script fallback, and the band ships `hidden`: nobody without
        JavaScript ever sees this element, so there is nothing to fall back
        FOR.

        The `outline` is gone with them -- the mockup suppresses the focus
        ring inline and repaints it from script. US-5.4's CORRECTION 3
        settled that: the native ring, via `:focus-visible`, in CSS.
        """
        canvas = _open_tag(self._home(), CANVAS_ID)

        for attribute in ("width=", "height=", "style=", "outline"):
            with self.subTest(attribute=attribute):
                self.assertNotIn(attribute, canvas)

    def test_the_band_sits_outside_the_decoration_layer(self, *_mocks):
        """**NFR-8**: the layer takes no clicks, so the game cannot live in it.

        `#decor` is `aria-hidden` and `pointer-events:none` wholesale, and
        `test_decor.py` greps it for exactly the things this band needs -- a
        `tabindex`, a focusable element. A game inside it would be announced
        to nobody and clickable by nobody. It belongs in `#page` with the
        work, which is also why it adds no rung to the ladder.
        """
        home = self._home()

        self.assertNotIn(CANVAS_ID, _element(home, LAYER_ID))
        self.assertIn(CANVAS_ID, _element(home, "page"))

    def test_the_band_carries_no_colour_of_its_own(self, *_mocks):
        """Colour reaches the band through tokens, like everything else.

        The mockup writes `color:var(--muted)` and `border-color` literals
        side by side; the literals are what made the old markup stay Arcade
        in every world. `test_theme.py` owns this rule for the template
        SOURCE across all five page templates -- what is checked here is the
        band's RENDERED markup, which is where an interpolated value would
        show up and the source scan would not see it.
        """
        self.assertEqual(_colour_literals(_element(self._home(), BAND_ID)), [])

    def test_the_band_still_ships_in_a_world_that_hides_it(self, *_mocks):
        """AC 8: the gate is a stylesheet's job, never a template condition.

        **F-18** owns "two worlds render identical bytes"; what is owned here
        is the mistake that would satisfy AC 8 while breaking it. Wrapping
        the band in a template `if` would hide it from Just the Work
        correctly and be wrong twice over: the bytes would differ, and the
        chooser swaps worlds with NO page load, so a server-side answer
        arrives too late to be an answer at all.

        Just the Work is the one world asked, because it is the one a render
        can be PINNED to. The withdrawing half belongs to the stylesheet
        suite below (`SideQuestStylesheetTests`), not to this test -- which
        is why the name says "a world" rather than "every world".

        `test_decor.py` pins the same property for the cast one story
        earlier, for the same reason.
        """
        self.assertIn(f'id="{CANVAS_ID}"', self._home({THEME_PARAM: CLEAN}))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class SideQuestScriptTests(SimpleTestCase):
    """The game script -- the contracts a render can still see."""

    def _script(self):
        """The game's source: the one owned script that mentions the canvas."""
        return _inline_script(
            self.client.get(reverse("ui:home")).content.decode(), SCRIPT_MARKER
        )

    def _code(self):
        """That source with the `//` commentary dropped.

        The script explains at length why it must not touch storage and why
        it binds the key on the canvas -- so a comment that merely says
        `localStorage` would read as an unguarded access and fail a test
        about code that never existed.
        """
        return "\n".join(_code_lines(self._script()))

    def test_space_is_bound_on_the_canvas_and_never_on_the_document(self, *_mocks):
        """AC 3, and the defect most likely to make the whole site look broken.

        Bound to the document, `preventDefault` on Space stops the page
        scrolling for every visitor on it, whether or not they ever noticed
        the game. On a portfolio that reads as a site that does not work --
        and it would be reported as a scrolling bug, not as a game.

        The by-hand half (press Space unfocused, the page scrolls) is the
        story's Verification block; what a render can prove is WHAT the
        listeners are attached to.

        The RECEIVERS are collected and checked, rather than one spelling
        asserted: `cvs.addEventListener("keydown"` would pin the local
        variable's name and the quote style, and fail on a rename that
        changes nothing. What may not change is that neither input listener
        is on `document` or `window`.
        """
        code = self._code()
        receivers = set(
            re.findall(r"(\w+)\.addEventListener\(\s*[\"'](?:keydown|pointerdown)", code)
        )

        self.assertTrue(receivers, "no input listeners found -- the regex has drifted")
        self.assertEqual(receivers & {"document", "window"}, set())
        self.assertNotIn("document.addEventListener", code)

    def test_touch_jumps_and_takes_the_focus_it_suppressed(self, *_mocks):
        """AC 7: a tap jumps, once, and leaves the strip focused.

        `preventDefault` on `pointerdown` is what stops the compatibility
        mouse events firing a second jump -- and it suppresses the browser's
        own focus-on-press along with them, which is why the focus is moved
        by hand immediately after. The two belong together; the mockup
        comments the pair and so does the script.
        """
        body = _function_body(self._script(), "onPointerdown", INDENT)

        self.assertIn("preventDefault", body)
        self.assertIn(".focus()", body)

    def test_the_loop_asks_the_switch_and_ends_by_not_rescheduling(self, *_mocks):
        """AC 4: cancelled, not left running invisibly.

        This is the only continuously-running JavaScript on the site, and it
        is the one thing in the build that no stylesheet can stop: US-5.5's
        `.no-motion *{animation:none}` reaches CSS animations and nothing
        else. So the script has to ask -- and `window.axePrefs.effects()` is
        REMOVE EFFECTS and the OS reduced-motion preference already collapsed
        into one answer by the store, which is why there is no `matchMedia`
        here. `setInterval` would be a second clock nothing cancels.

        That the loop ACTUALLY stopped is measured, not asserted: the story's
        Q3 records the trace. There is deliberately no `cancelAnimationFrame`
        to assert -- both of the loop's exits run inside the frame they end,
        so the only id there is to cancel is the one already executing, and
        a loop that does not reschedule itself has stopped. Asserting the
        call would have pinned a no-op and made it look like the mechanism.
        """
        code = self._code()

        self.assertIn("axePrefs.effects()", code)
        for forbidden in ("matchMedia", "setInterval"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, code)

    def test_the_world_is_asked_of_the_stylesheet(self, *_mocks):
        """US-6.5's idiom: the sheet already knows, so do not ask it twice.

        `getClientRects()` is empty for an element the gate is holding at
        `display:none`, so ONE question answers the gate rule, Just the Work
        and a live swap away from Arcade at once. The alternative is a list
        of worlds in JavaScript, which is a second answer to a question
        `ROOT_CLASSES` and the gate rule already answer -- and it would drift
        the day a world is added, silently, in the direction of a skater
        appearing where nobody put one.
        """
        code = self._code()

        self.assertIn("getClientRects", code)
        self.assertNotIn("documentElement.classList", code)

    def test_nothing_persists_and_no_colour_is_spelled_here(self, *_mocks):
        """The high score does not survive the page, deliberately (Q1).

        `window.axePrefs` is the one place in this codebase that touches
        storage and owns **NFR-7**'s guards; a fourth key would be a
        validation path, a `KEYS` edit in a done story's test and a readout
        nobody asked for. So the game reaches storage nowhere.

        And it spells no colour. The mockup carries twelve hex literals plus
        three un-tokened greys -- a second copy of Arcade's `:root` block,
        which is exactly what the token layer was built to end. The palette
        is read back off the page instead.
        """
        code = self._code()

        self.assertNotIn("localStorage", code)
        self.assertNotIn("rgba(", code)
        self.assertEqual(HEX.findall(code), [])
        self.assertRegex(code, r"getPropertyValue\(\s*[\"']--")
        self.assertNotIn("console.", code)

    def test_the_band_is_revealed_by_the_script_that_owns_it(self, *_mocks):
        """The other half of "ships hidden": something has to turn it on.

        The decoration layer is revealed by the script that owns the
        controls; this band is revealed by its own, because its own is the
        only one that knows the canvas exists.
        """
        self.assertRegex(self._code(), r"\.hidden = false")

    def test_every_function_fits_on_a_screen(self, *_mocks):
        """AC 11, mechanically -- the cap no linter in this repo can enforce.

        ruff, flake8 and pylint never read a line of this game, so "functions
        ≤20 lines, ≤5 args" would otherwise be a comment that cannot fail.
        The mockup's game loop and its paint routine each do several
        unrelated jobs in one function; both are split here, and this is
        what holds them split.

        The floor is ONE function, not a count: a count would have to be
        edited every time something is merged or inlined, and what it is
        really guarding is that the regex still matches the house style at
        all. The repo's own `the regex has drifted` idiom.
        """
        script = self._script()
        found = DECLARATION.findall(script)

        self.assertTrue(found, "no functions found -- the regex has drifted")
        for name, arguments in found:
            with self.subTest(function=name):
                # `_function_body` returns the INTERIOR, and the slice opens
                # with the newline after `{` -- so it is stripped first, or
                # `splitlines` reports one blank line that is not there. Then
                # the signature and the closing brace are added back, because
                # AC 11 says "functions ≤20 lines" and a function measured by
                # its interior alone gets two free ones.
                body = _function_body(script, name, INDENT).strip("\n")
                self.assertLessEqual(len(body.splitlines()) + 2, MAX_LINES)
                self.assertLessEqual(len(arguments.split(",")), MAX_ARGS)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class SideQuestStylesheetTests(SimpleTestCase):
    """One gate, one focus ring, and no new rung on the ladder."""

    def _sheet(self):
        """The stylesheet, comments stripped."""
        return _css(self.client.get(reverse("ui:home")).content.decode())

    def test_one_rule_withdraws_the_band_from_every_other_world(self, *_mocks):
        """AC 8 and Q1: Arcade only, in ONE rule, derived from the vocabulary.

        Every other cast in this sheet is gated by its complement --
        `:root:not(.manor) .manor-cast`. This one cannot be: Arcade's root
        class is the EMPTY STRING, because Arcade IS `:root`, so there is no
        class to negate and the complement has to be written out world by
        world. That makes it the one gate a fifth world would slip through
        unnoticed, which is why the expectation is built from `ROOT_CLASSES`
        rather than typed -- adding a world fails this test instead of
        putting a skater in it.

        `display:none` rather than `visibility:hidden` for the reason Just
        the Work withdraws the scares switch the same way: the canvas is a
        TAB STOP, and an invisible one is still in the tab order and still
        announced. Gone has to mean gone from both.
        """
        sheet = self._sheet()
        # `_rules_naming` matches back to the previous rule's brace, so each
        # hit arrives wearing the blank line and indentation in front of it.
        naming = [rule.strip() for rule in _rules_naming(sheet, GATE_CLASS)]

        self.assertEqual(naming, [f"{EXPECTED_GATE}{{"])
        self.assertIn("display:none", _declaration_block(sheet, EXPECTED_GATE))

    def test_the_canvas_has_a_visible_focus_ring_in_the_stylesheet(self, *_mocks):
        """AC 5 / **F-14**: the one focusable thing has to LOOK focusable.

        `:focus-visible` rather than `:focus` so a mouse or a tap does not
        paint a ring nobody asked for, and in CSS rather than the mockup's
        `focus`/`blur` listeners assigning a `boxShadow` -- US-5.4's
        CORRECTION 3. `touch-action:none` is the touch half of AC 7: without
        it the browser spends the first moment of a tap deciding whether it
        is the start of a scroll, and the jump arrives late or not at all.

        US-7.3 moved the ring rather than removing it. This canvas used to
        carry its own `#sk-canvas:focus-visible` copy of the declaration;
        that story found only a handful of elements had an authored ring and
        the rest fell through to the browser's, so the same declaration
        became one site-wide rule and the copies collapsed into it. The
        guarantee is unchanged and now stronger -- what this asserts is that
        the shared rule exists and that nothing on the canvas takes it back,
        which is the only way the canvas could still lose it.
        """
        sheet = self._sheet()

        self.assertIn(RING_DECLARATION, _declaration_block(sheet, SITE_WIDE_RING))
        declared = _declaration_block(sheet, f"#{CANVAS_ID}")
        self.assertIn("touch-action:none", declared)
        # Subsumes the `outline:none` this used to check: ANY outline of the
        # canvas's own would now override the shared ring, not only that one.
        self.assertNotIn("outline:", declared)

    def test_the_band_adds_no_rung_to_the_ladder(self, *_mocks):
        """It is CONTENT, at `#page`'s `z-index:1`, not an overlay.

        Nine rungs are ranked against each other in THE LADDER above, and the
        reason that comment can be read as a complete list is that nothing
        joins it quietly. A band in normal flow under the hero needs no rung,
        no `!important` and no animation -- and if it ever grows one, the
        ladder's comment has become a lie and this fails first.
        """
        sheet = self._sheet()
        rules = _rules_naming(sheet, GATE_CLASS) + self._band_rules(sheet)

        self.assertTrue(rules, "no band rules found -- the regex has drifted")
        for rule in rules:
            selector = rule.strip().rstrip("{")
            with self.subTest(rule=selector):
                block = _declaration_block(sheet, selector)
                for forbidden in ("z-index", "!important", "animation"):
                    self.assertNotIn(forbidden, block)

    @staticmethod
    def _band_rules(sheet):
        """Every selector in `sheet` naming the band or its canvas."""
        return re.findall(r"[^{}]*(?:sk-|side-quest)[^{}]*\{", sheet)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class SideQuestWithoutJavaScriptTests(SimpleTestCase):
    """AC 10: scripts off, and the page is still a portfolio."""

    def test_the_page_is_a_portfolio_with_the_scripts_stripped(self, *_mocks):
        """**A1**, the governing rule, asserted the way every story asserts it.

        The game is the most purely-for-fun thing in the build and the one
        with the clearest potential to get between a client and the work. So
        the test is not "does the game degrade" -- it is "is the work still
        there when the game is not". The band stays `hidden` because the
        script that reveals it is the script that was stripped, and the hero,
        the projects and the contact route are all untouched.
        """
        html = _without_scripts(
            self.client.get(reverse("ui:home")).content.decode()
        )

        _assert_work_survives_without_scripts(self, html)
        self.assertIn(" hidden>", _open_tag(html, BAND_ID))
        for copy in ("SOLUTION", "ARCHITECT", "VIEW PROJECTS"):
            with self.subTest(copy=copy):
                self.assertIn(copy, html)
