"""Tests for the control that strips the site to stillness.

A separate module for the reason `test_theme.py`, `test_hire_me_panel.py`,
`test_preferences.py` and `test_chooser.py` each record: `tests.py` is already
over 800 lines against pylint's `too-many-lines` ceiling of 1000. The story's
Scope names `tests.py` because it was written before that split; the split is
the newer decision and the one the repo follows.

**Django renders templates; it does not run them.** So nothing here proves the
control WORKS -- not that pressing it stills the page, not that the state
survives a reload, not that an explicit choice beats the system preference.
Those are the story's Verification block and were done by hand. Three
properties a render genuinely carries are pinned here instead, and they are
the three that fail silently:

1. **The control is absent, not dead, without JavaScript.** It ships inside a
   cluster the server renders `hidden`, exactly as US-5.4's way back does. A
   button whose only job needs a script, rendered visible, is worse than no
   button at all (**A1**).
2. **The server never ships the stillness class.** It cannot read a
   preference that lives in the browser, so it must not guess one -- a guess
   is a visitor's chosen world arriving still, or their chosen stillness
   arriving in motion.
3. **The stacking order.** The control has to sit above everything the site
   draws and below the dialog that owns the screen. It is four numbers in a
   stylesheet, nothing on any page looks wrong when one of them is edited,
   and epic 6 is about to build nine overlays against it (**F-17**).
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import THEME_PARAM
from .test_chooser import CHOOSER_MARKER, _css, _open_tag
from .test_preferences import (
    _assert_work_survives_without_scripts,
    _inline_script,
    _owned_script,
    _render_every_page,
    _without_scripts,
)
from .test_theme import _declaration_block, _root_tag, _rules_naming, _world_join
from .tests import AVAILABILITY, PROJECTS, SKILLS

CONTROL_ID = "toggle-effects"
STILL_CLASS = "no-motion"

# The mockup's four strings, which F-18 freezes: a world changes the palette,
# never the words.
LABELS = ("REMOVE EFFECTS", "RESTORE EFFECTS")

Z_INDEX = re.compile(r"z-index:(\d+)")


def _z(css, selector):
    """The `z-index` declared in `selector`'s own rule.

    Bounded to the rule by `_declaration_block`, which anchors on the
    selector with its opening brace attached. That matters for the two
    overlays: `body::after{` is also a substring of the stillness rule and of
    Just the Work's, and both of those come later in the stylesheet, so the
    base rule is the one found.
    """
    found = Z_INDEX.search(_declaration_block(css, selector))
    assert found is not None, f"no z-index in {selector!r}"
    return int(found.group(1))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class StillnessControlMarkupTests(SimpleTestCase):
    """What the server actually sends, on every page a visitor can reach."""

    def _home(self, query=None):
        """The home page's HTML, optionally pinned to a world."""
        return self.client.get(reverse("ui:home"), query or {}).content.decode()

    def _pages(self):
        """The three renders of `base.html`, from the shared helper."""
        return _render_every_page(self.client)

    def test_the_control_ships_inside_the_hidden_cluster_on_every_page(self, *_mocks):
        """AC 9 and AC 13, and the assertion this story exists to protect.

        Three things at once, because they are one property. The control is
        on the page; it is INSIDE `#site-controls` and before the way back,
        so it is first in Tab order; and the cluster carries `hidden` in the
        bytes the server sends. Take the last away and a visitor with
        JavaScript off meets a button that cannot do the one thing it names.

        Asserted per page because `base.html` has three renderers and one of
        them is not ours -- Django's own `page_not_found`. A mechanism wired
        into a view would be absent exactly there, on the page a visitor
        reaches by mistake and most wants a way out of.
        """
        for name, html in self._pages().items():
            with self.subTest(page=name):
                cluster = html[html.index('id="site-controls"'):html.index('id="open-chooser"')]
                self.assertIn(f'id="{CONTROL_ID}"', cluster)
                self.assertIn(" hidden>", _open_tag(html, "site-controls"))

    def test_the_control_is_a_labelled_toggle(self, *_mocks):
        """AC 5 and AC 7: a real button, in a state, saying what it will do.

        `aria-pressed` is what makes it a toggle rather than a thing that
        happens, and it is also what earns the pressed styling every world
        already defines. The `aria-label` carries the ACTION because the
        visible text is two words in a display face; "REMOVE EFFECTS" alone
        does not say what it removes them from.

        A `<button>` rather than a styled `<div>` is the whole of AC 7: it is
        keyboard-reachable and Space/Enter-operable by construction, which is
        a property no assertion here could add and none can take away.
        """
        tag = _open_tag(self._home(), CONTROL_ID)

        self.assertIn('type="button"', tag)
        self.assertIn('aria-pressed="false"', tag)
        self.assertIn("aria-label=", tag)
        self.assertIn(f">{LABELS[0]}</button>", self._home())

    def test_the_server_never_ships_the_class(self, *_mocks):
        """AC 2 and AC 4: the preference lives in the browser, so the server does not guess.

        The class arrives from the store, before paint, on the client. If the
        server ever put it on `<html>` it would be guessing for every visitor
        at once -- and the guess is visible both ways round: a visitor who
        chose motion gets a still page, a visitor who asked for stillness
        gets it only after their own script corrects it.

        Checked on a pinned render too, because `?theme=` is the one thing
        that CAN change the root tag and is therefore the one place a
        stillness class could plausibly be smuggled in.
        """
        for query in (None, {THEME_PARAM: "clean"}, {THEME_PARAM: "horror"}):
            with self.subTest(query=query):
                self.assertNotIn(STILL_CLASS, _root_tag(self._home(query)))

    def test_the_page_reads_without_the_control(self, *_mocks):
        """AC 9 and AC 13's second half: the work survives the visitor who cannot run it.

        `test_preferences.py` pins this for the store and `test_chooser.py`
        for the dialog. Repeated here because the thing being guarded
        changed: this story adds a second fixed, always-on-screen element to
        every page, which is exactly the kind of addition that quietly takes
        a site away from someone who cannot dismiss it.

        The cluster's `hidden` attribute is NOT re-asserted here -- the test
        above already pins it on all three pages, and it is static markup, so
        stripping the scripts cannot change it. What is unique to this test
        is the half that could change: the work still being on the page.
        """
        _assert_work_survives_without_scripts(self, _without_scripts(self._home()))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class StillnessScriptTests(SimpleTestCase):
    """Which script owns what -- the half a template render can see."""

    def _home(self):
        """The home page's HTML."""
        return self.client.get(reverse("ui:home")).content.decode()

    def test_the_store_applies_the_class_before_paint(self, *_mocks):
        """AC 1 and AC 2: one apply path, and it runs in `<head>`.

        Two orderings, both invisible on the page and both load-bearing.

        The class is applied from the STORE, so there is exactly one place
        that decides what the root element wears -- the same property
        `test_chooser.py` pins for the world. The control never touches it.

        And the call sits ABOVE the pinned-render guard, because `?theme=`
        pins the world and nothing else: a tester looking at one world keeps
        their own stillness. Below that guard, every `?theme=` render would
        silently ignore the preference.
        """
        owned = _owned_script(self._home())

        self.assertIn(STILL_CLASS, owned)
        self.assertLess(owned.index("applyEffects(effects())"), owned.index("if (pinned)"))
        self.assertNotIn(STILL_CLASS, _inline_script(self._home(), CHOOSER_MARKER))

    def test_the_control_writes_only_through_the_store(self, *_mocks):
        """AC 2: the control is a view, and the store owns NFR-7's guards.

        US-5.3 put every `localStorage` access behind a `try` in one script
        and `test_preferences.py` counts them -- exactly two. A control
        reaching storage directly would be a third, free to get a private
        window wrong, and that count would stop meaning what it says.
        """
        script = _inline_script(self._home(), CHOOSER_MARKER)

        self.assertIn("window.axePrefs.setEffects(", script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("console.", script)

    def test_the_label_is_corrected_before_the_cluster_is_revealed(self, *_mocks):
        """AC 5: the no-flash ordering, which nothing else would catch.

        The server renders the effects-on wording because it has no
        preference to read. For a visitor who chose stillness that wording is
        wrong, and the script fixes it -- but only if it fixes it while the
        cluster is still `hidden`. The other way round, every page load shows
        REMOVE EFFECTS flipping to RESTORE EFFECTS after the paint.

        Swap these two lines and every other test in this file stays green.

        `rindex`, and the count beside it, are not fussiness -- the first
        draft of this test used `index` and could not fail. The call is made
        TWICE: once by the click listener, which sits earlier in the script
        than the reveal does, so the earliest occurrence is before
        `controls.hidden` however the reveal is ordered. The count is what
        then stops the whole assertion being satisfied by the listener alone
        if the reveal-time call is deleted outright.
        """
        script = _inline_script(self._home(), CHOOSER_MARKER)

        self.assertEqual(script.count("renderStillness();"), 2)
        self.assertLess(
            script.rindex("renderStillness();"), script.index("controls.hidden = false")
        )


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class StillnessStylesheetTests(SimpleTestCase):
    """One class, one block, and the stacking order epic 6 inherits."""

    def _home(self):
        """The home page's HTML."""
        return self.client.get(reverse("ui:home")).content.decode()

    def _css(self):
        """The stylesheet as rendered on the home page, commentary removed.

        The strip is what makes the counting below honest: every word of
        prose in that stylesheet renders into every page, and this story's
        own comment names the class repeatedly. Counted against the raw
        stylesheet, a comment could satisfy -- or break -- an assertion about
        how many RULES there are.
        """
        return _css(self._home())

    def test_stillness_is_one_block_and_not_a_list(self, *_mocks):
        """AC 12: the property that keeps this story from rotting.

        Two rules. Not nine, and not nine-plus-one-per-creature as epic 6
        lands: a per-animation opt-out list is a list somebody has to
        remember to add to, and the whole reason this story ships BEFORE the
        things it withdraws is that nobody will.

        `WORLD_JOIN` is the other half, and it guards a mistake that is
        silent rather than ugly: `test_theme.py` finds a world's palette by
        its class name followed by an opening brace, so a rule joining this
        class to a world's would be found first and read as that world's
        palette -- for every token the suite checks.
        """
        css = self._css()

        self.assertEqual(len(_rules_naming(css, STILL_CLASS)), 2)
        self.assertIsNone(
            _world_join(css, STILL_CLASS), "a world class is joined to the stillness class"
        )

    def test_stillness_withdraws_the_overlays_in_every_world(self, *_mocks):
        """AC 1: the scanlines and the vignette go, and they go for all four worlds.

        `display:none`, not a fainter gradient -- Just the Work already
        records that a quieter scanline is still a scanline. The base rules
        must survive: stillness withdraws them for a visitor who asked, it
        does not delete them for everyone.
        """
        css = self._css()

        withdrawn = _declaration_block(
            css, f".{STILL_CLASS} body::before,.{STILL_CLASS} body::after"
        )
        self.assertIn("display:none", withdrawn)
        for overlay in ("body::before", "body::after"):
            with self.subTest(overlay=overlay):
                self.assertIn(f"\n  {overlay}{{", css)

    def test_the_control_sits_above_the_glass_and_below_the_chooser(self, *_mocks):
        """AC 6 (F-17): the ladder, pinned as an ORDER rather than four numbers.

        The control must clear the scanlines and the vignette, because a
        control painted through a corner the vignette darkens to 90% black is
        reachable in the sense that a click lands on it and unreachable in
        the sense that matters. And it must stay under the chooser, which
        claims `aria-modal` and traps Tab -- US-5.4's recorded decision, and
        a claim the dialog cannot honour with a live button floating over it.

        Asserted as `<` rather than as the values, so retuning the ladder is
        a free change and INVERTING it is not. Epic 6 builds beneath all of
        this: its own ceiling is 455.
        """
        css = self._css()

        self.assertLess(_z(css, "body::after"), _z(css, "body::before"))
        self.assertLess(_z(css, "body::before"), _z(css, "#site-controls"))
        self.assertLess(_z(css, "#site-controls"), _z(css, ".chooser"))

    def test_the_stylesheet_reads_no_os_motion_preference(self, *_mocks):
        """AC 4: the system preference is read once, and not here.

        This is the fight the story warned about. The stylesheet used to gate
        the logo flicker and the chooser cards on a media query, which cannot
        know a visitor stored a preference -- so someone who turned the
        effects back ON despite their system setting had the class removed
        and still saw nothing move. The switch doing nothing, for exactly the
        people most likely to press it.

        So the preference is read in the store's `prefersCalm()` and
        expressed as the class. This pins the absence, because a media query
        is the obvious thing for epic 6 to reach for and reintroducing one
        would restart the fight silently.
        """
        self.assertNotIn("prefers-reduced-motion", self._css())
        self.assertIn("prefers-reduced-motion", _owned_script(self._home()))

    def test_the_cluster_wraps_at_phone_width(self, *_mocks):
        """AC 10: two controls that stay on a 320px screen, and stay tappable.

        Layout needs a browser and the by-hand check is the real gate. What a
        text assertion can hold is the specific mistake: two display-face
        buttons measure about 340px side by side, and a fixed row anchored to
        the right grows LEFTWARDS -- off the screen, where nothing scrolls it
        back. Wrapping is what makes the second row stack instead.

        The 44px floor is asserted beside it because US-5.6 adds a third
        button to this same cluster, and a wrap that produced three 34px
        targets would satisfy the first half of this story's AC 10 while
        breaking the second.
        """
        css = self._css()

        self.assertIn("flex-wrap:wrap", _declaration_block(css, "#site-controls"))
        self.assertIn("min-height:44px", _declaration_block(css, "#site-controls .btn"))
