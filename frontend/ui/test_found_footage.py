"""Tests for Found Footage's blood band, pool, handprints and tracking band.

A separate module for the reason `test_theme.py`, `test_hire_me_panel.py`,
`test_preferences.py`, `test_chooser.py`, `test_effects.py`, `test_scares.py`
and `test_decor.py` each record: a module near pylint's `too-many-lines`
ceiling takes no more. `test_decor.py` is the one that is full -- it already
carries both US-6.1's stage and US-6.2's cast -- so US-6.3's world lands
here. The story's Scope names `tests.py` because it was written before that
split; the split is the newer decision and the one the repo follows.

**What this module does NOT re-assert.** Everything US-6.3 ships lives inside
`#decor`, and containment is what makes the layer's existing guarantees cover
it for free: `test_decor.py` already walks the container on all three pages
for anything focusable or clickable (AC 7), and `test_effects.py` already
pins that ONE rule withdraws the whole container for REMOVE EFFECTS (AC 10)
and that the stylesheet reads no OS motion preference (AC 11). Re-asserting
any of those here would be a second copy to keep in step. What is left is
what is genuinely this world's: the gate, the rungs, the clocks, the geometry
that keeps blood off the nav, and the token the artwork reaches colour
through.
"""

import re
from itertools import combinations
from math import gcd
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, HORROR, MANOR, THEME_PARAM
from .test_chooser import _css
from .test_decor import DURATION, HORROR_CAST, STYLED_TAG, _element
from .test_effects import LAYER_ID, _z
from .test_preferences import _inline_script, _render_every_page
from .test_theme import CSS_RULE, _colour_literals, _declaration_block, _sections
from .tests import AVAILABILITY, PROJECTS, SKILLS

# The five elements and how many of each the world carries. Written out
# because the COUNT is the decision: two handprints rather than one is what
# makes the glass look leaned on instead of decorated, and a sixth element
# added without a rung would pass a count-free test.
BAND = {"blood": 1, "pool": 1, "hand": 2, "tracking": 1}

# The mockup's droplets. Thirteen tempos, none of them shared -- AC 4 is a
# statement about the SPREAD, so the count is part of the assertion.
DROPLETS = 13

# The rung each element takes, from US-6.1's ladder. The hands share 26 with
# `#mist`, which is Manor's and never co-renders; the tape sits at 28, over
# the glass and under the blood.
RUNGS = {".hand": 26, ".tracking": 28, ".pool": 399, ".blood": 400}

# The one rule that withdraws the whole world, and the class it reads.
WORLD_GATE = f":root:not(.{HORROR}) .{HORROR_CAST}"

# The three elements that keep a clock of their own. The band is absent on
# purpose: its tempo is per-droplet and lives in the markup, not in a rule.
CLOCKED = (".pool", ".hand", ".tracking")

# The whole-second duration out of an `animation:` shorthand. The clocks test
# READS the tempos with this and computes on them, rather than confirming
# three literals are present -- three different numbers that share a factor
# would satisfy a literal pin and still lock visibly.
CLOCK_SECONDS = re.compile(r"animation:\w+ (\d+)s")

# The runtime-measured nav height, and the class that reads it. Blood hangs
# from the nav's bottom edge by GEOMETRY -- every rung outranks the nav in
# the stacking order, so nothing else keeps it off the brand.
NAV_VAR = "--navh"
NAV_ANCHOR = "under-nav"

# The colour, declared in this world's palette block and read only by the
# artwork's fill/stroke.
BLOOD = "--blood"

# The measurement's CSS fallback, captured so AC 3 can assert it is not zero:
# a failed measurement must hang the band at the nav's resting height, never
# across the brand at the top of the viewport.
#
# Anchored on the `var()` alone and deliberately NOT on a `top:` prefix. The
# duplicate this guards against is an inline `top:calc(var(--navh,43px) +
# 60px)` on the handprint, and a pattern expecting `top:var(` reads straight
# past it -- which is exactly the copy the transform exists to avoid.
NAV_FALLBACK = re.compile(rf"var\({NAV_VAR},(\d+)px\)")

# The 72-second cycle's subscription class, which nothing here may wear.
CROSSING = "crossing"


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class FoundFootageMarkupTests(SimpleTestCase):
    """The five elements, as the server sends them in every world."""

    def _layer(self, query=None):
        """The decoration layer's markup, from `<div id="decor"` to its close."""
        page = self.client.get(reverse("ui:home"), query or {}).content.decode()
        return _element(page, LAYER_ID)

    def test_the_whole_band_is_in_the_layer(self, *_mocks):
        """AC 1: four assets, five elements, and the count is the assertion.

        Counted inside `#decor` rather than anywhere on the page, because
        containment is what earns this story the layer's existing
        guarantees -- the focus walk, the click-transparency and the one
        rule that withdraws everything for REMOVE EFFECTS all scan that
        container and nothing outside it.
        """
        layer = self._layer()

        for name, expected in BAND.items():
            with self.subTest(element=name):
                self.assertEqual(len(re.findall(rf'class="{name} ', layer)), expected)

    def test_every_band_element_wears_the_world_it_belongs_to(self, *_mocks):
        """AC 6: the half a selector cannot protect.

        The gate is one rule reading one class, which is only as good as the
        markup wearing it. An element that forgets the class is not hidden
        anywhere -- it renders in all four worlds, which is the exact defect
        the gate exists to prevent and the one a stylesheet test cannot see.
        """
        layer = self._layer()

        for name in BAND:
            for classes in re.findall(rf'class="({name} [^"]*)"', layer):
                with self.subTest(element=classes):
                    self.assertIn(HORROR_CAST, classes.split())

    def test_the_droplets_fall_on_their_own_tempos(self, *_mocks):
        """AC 4: thirteen droplets, thirteen durations, none of them shared.

        Uniform droplets read as a CSS demo and staggered ones read as a
        ceiling, which is the same reasoning the 72s cycle applies at the
        scale of a whole world. Asserted as a SET as well as a count: a port
        that copied one droplet thirteen times would satisfy the count and
        lose the entire effect. Thirteen DISTINCT values is still not quite
        the claim, though: a droplet retimed to the layer's own 72s would
        keep the set distinct while rejoining the clock this world does not
        run on, so the shared duration is rejected by name as well.
        """
        layer = self._layer()
        tempos = re.findall(r'class="bd" style="animation-duration:([\d.]+s)', layer)

        self.assertEqual(len(tempos), DROPLETS)
        self.assertEqual(len(set(tempos)), DROPLETS)
        self.assertNotIn(DURATION, tempos)

    def test_nothing_in_this_world_takes_a_slot_on_the_shared_clock(self, *_mocks):
        """AC 5: the band keeps its own time, and the grid stays free.

        US-6.2 allocated the 72s cycle's delays across worlds and left 56 and
        63 expecting this story to claim them. It does not: every element
        here runs its own clock, so no element wears `crossing` and neither
        delay appears. Both halves are asserted, because wearing the class
        without a delay and taking a delay without the class are two
        different ways to end up back on the shared clock.
        """
        layer = self._layer()

        for classes, _style in STYLED_TAG.findall(layer):
            if HORROR_CAST in classes.split():
                with self.subTest(element=classes):
                    self.assertNotIn(CROSSING, classes.split())
        for delay in ("-56s", "-63s"):
            with self.subTest(delay=delay):
                self.assertNotIn(delay, layer)

    def test_the_band_ships_in_every_world_and_is_withdrawn_by_the_stylesheet(self, *_mocks):
        """F-18: the server sends one page, and CSS decides what it shows.

        A server-side test cannot assert that Manor renders no blood, because
        the markup it is handed is byte-identical in all four worlds -- that
        identity IS the contract. So this pins the half the server owns, and
        the gate rule below pins the half the stylesheet owns. Mirrors
        US-6.2's test of the same name, for the same reason.
        """
        for world in (MANOR, CLEAN, HORROR):
            with self.subTest(world=world):
                layer = self._layer({THEME_PARAM: world})
                self.assertIn(f'class="blood {HORROR_CAST}', layer)
                self.assertIn(f'class="tracking {HORROR_CAST}"', layer)

    def test_the_artwork_reaches_colour_only_through_the_token(self, *_mocks):
        """The token layer's rule: no literal in this markup gets to be a colour.

        NOT AC 9, despite being the nearest thing to it here. AC 9 is about
        the CONTRAST of this world's text, which is a measurement rather
        than an assertion -- those figures live in the story's
        Implementation notes. This is the narrower rule underneath it, the
        one that makes a per-world palette possible at all.

        `test_theme.py` pins the five page templates and deliberately
        excludes `base.html`; this is that rule applied to the layer's own
        markup, which is where a ported asset would smuggle one in. The
        mockup's blood is a four-world table of literals, so the port is
        exactly the moment the rule is easiest to break.
        """
        layer = self._layer()

        self.assertEqual(_colour_literals(layer), [])
        self.assertIn(f"var({BLOOD})", layer)

    def test_only_the_elements_that_hang_from_the_ceiling_read_the_nav(self, *_mocks):
        """AC 2: the band and the upper handprint, and nothing else.

        The pool is at the floor and the lower hand is anchored to it, so
        neither has any business knowing the nav's height. Asserted as a
        count rather than a presence: the failure worth catching is the
        anchor spreading to elements that do not need it, which would make
        a nav change move things it should never touch.
        """
        layer = self._layer()

        self.assertEqual(layer.count(NAV_ANCHOR), 2)
        self.assertIn(f'class="blood {HORROR_CAST} {NAV_ANCHOR}"', layer)
        self.assertIn(f'class="hand {HORROR_CAST} {NAV_ANCHOR}"', layer)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class FoundFootageScriptTests(SimpleTestCase):
    """The one piece of this world that is JavaScript rather than CSS."""

    def test_the_nav_is_measured_by_the_script_that_wakes_the_layer(self, *_mocks):
        """AC 2: one script knows about the layer, and it is this one.

        The measurement could have been a third inline script and is not: the
        block that reveals `#decor` is already the one place that knows the
        layer exists, and a second place to look is how the two drift apart.
        Run over all three pages because `base.html` has three renderers and
        one of them is Django's own 404 -- a measurement wired into a view
        would be present on two and missing on the third.
        """
        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                script = _inline_script(html, NAV_VAR)
                self.assertIn("decor.hidden = false", script)

    def test_the_band_is_measured_before_the_layer_is_revealed(self, *_mocks):
        """The ordering, which is the difference between a jump and a paint.

        Reveal first and the band's first frame hangs at the CSS fallback,
        then snaps to the measured height once the script catches up. The
        visitor sees the correction. Measuring first means the first frame
        is already right, which is the same reasoning that puts the whole
        preference store at the top of `<head>`.
        """
        script = _inline_script(self._home(), NAV_VAR)

        self.assertLess(script.index(NAV_VAR), script.index("decor.hidden = false"))

    def test_the_measurement_is_guarded_on_both_things_that_can_be_missing(self, *_mocks):
        """AC 3 and NFR-7: neither the observer nor the nav is promised.

        `ResizeObserver` is absent in old browsers and `<nav>` is absent on
        two of the three pages, and an unhandled throw in this block costs
        the visitor the reveal that follows it -- the whole decoration layer,
        for a decoration. The resize listener is the observer's FALLBACK and
        not its companion: registering both, as the mockup does, measures
        twice on every frame of a drag.

        A STRUCTURAL PIN, and worth naming as one: it asserts the source
        reads a particular way rather than that the behaviour holds, so a
        harmless rewording of either guard fails it. That is the honest
        limit of a server-side test over a client-side script -- nothing
        here executes it. It earns its place by catching the guard being
        DELETED, which is the change that actually costs a visitor the
        layer; the browser pass is what confirms it works.
        """
        script = _inline_script(self._home(), NAV_VAR)

        self.assertIn("window.ResizeObserver && nav", script)
        self.assertIn("nav ? nav.offsetHeight : 0", script)
        self.assertNotIn("console.", script)

    def _home(self):
        """The home page's HTML."""
        return self.client.get(reverse("ui:home")).content.decode()


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class FoundFootageStylesheetTests(SimpleTestCase):
    """The gate, the rungs, the clocks and the token."""

    def _sheet(self):
        """The stylesheet, comments stripped."""
        return _css(self.client.get(reverse("ui:home")).content.decode())

    def test_one_rule_withdraws_the_band_from_every_other_world(self, *_mocks):
        """AC 6: the gate is a rule, not a list.

        The same shape US-6.2 proved for Manor's cast, with the world
        swapped -- including the reason `:not()` is the only form that
        works, which is that Arcade's root class is the empty string and so
        cannot be named positively.

        The second assertion counts WITHDRAWAL rules specifically, not every
        rule that happens to mention the class. Counting mentions would tie
        this test to the unrelated `svg` sizing rule beside it -- a number
        any legitimate group rule would break, and one a replaced gate would
        still satisfy. What must stay singular is the HIDING: a world gated
        by one rule per element is the maintenance burden the shared class
        exists to avoid.
        """
        css = self._sheet()
        hiding = [selector.strip() for selector, block in CSS_RULE.findall(css)
                  if HORROR_CAST in selector and "display:none" in block]

        self.assertIn(f"{WORLD_GATE}{{display:none}}", css)
        self.assertEqual(hiding, [WORLD_GATE])

    def test_each_rung_takes_the_number_the_ladder_allocated(self, *_mocks):
        """AC 1, and the ceiling epic 6 agreed to stay under.

        US-6.1 wrote 399 and 400 into the ladder before a line of blood
        existed, and this story allocated 28 for the tape the same way. The
        numbers are checked against that table rather than merely against
        each other, so a rung quietly promoted above the glass fails here
        and not in a browser.
        """
        css = self._sheet()

        for selector, rung in RUNGS.items():
            with self.subTest(selector=selector):
                self.assertEqual(_z(css, selector), rung)

    def test_the_droplet_rule_names_its_path_and_never_its_duration(self, *_mocks):
        """AC 4: longhand, for the reason the cast's block already records.

        The mockup writes `animation:fall linear infinite` and then overrides
        the duration inline on every droplet, which works only because an
        inline style outranks the rule the shorthand has already written
        `animation-duration:0s` into. The day someone adds a more specific
        rule the shorthand wins and all thirteen droplets stop. Longhand
        means the tempo has exactly one home, and it is the markup.
        """
        block = _declaration_block(self._sheet(), ".bd")

        self.assertIn("animation-name:fall", block)
        self.assertNotIn("animation:", block)
        self.assertNotIn("animation-duration", block)

    def test_the_pool_the_hands_and_the_tape_keep_their_own_clocks(self, *_mocks):
        """AC 5: three tempos, independent of each other.

        11s, 9s and 7s are pairwise coprime, so no two of them come back
        into phase inside any span a visitor watches. That is the property
        that makes the world feel unscheduled, so the PROPERTY is what is
        asserted and the mockup's particular numbers are not. Three
        distinct tempos, pairwise coprime: that is the whole claim, and a
        later story free to retime the pool to 13s should not have to edit
        a test to do it. Pinning `[7, 9, 11]` instead would be the easier
        thing to write and would assert something nobody needs -- and it
        would make the coprime check dead, since those three are coprime by
        arithmetic and the check could never fail while the pin held.

        Distinctness is half of it and not a formality: `gcd(1, 1)` is 1,
        so three clocks all set to the same value are "pairwise coprime"
        and perfectly locked.

        Independence from the layer's own 72s cycle is deliberately NOT
        asserted, and the stylesheet comment says why: the hands' `seep` is
        `alternate`, so its real period is 18s and 72 is exactly four of
        those. It locks arithmetically and cannot lock visibly, because
        every subscriber to that cycle is `manor-cast` and none renders in
        this world. An assertion of independence from 72 could only be
        false or vacuous, so there is none.
        """
        css = self._sheet()
        blocks = "".join(_declaration_block(css, sel) for sel in CLOCKED)
        tempos = [int(found) for found in CLOCK_SECONDS.findall(blocks)]

        self.assertEqual(len(tempos), len(CLOCKED))
        self.assertEqual(len(set(tempos)), len(CLOCKED))
        for pair in combinations(tempos, 2):
            with self.subTest(pair=pair):
                self.assertEqual(gcd(*pair), 1)

    def test_a_failed_measurement_still_hangs_the_band_somewhere_sane(self, *_mocks):
        """AC 3: the fallback is the nav's real height, and never zero.

        "Guarded" for this element does not mean "does not throw" -- it means
        the band lands somewhere a reader can live with when the script never
        runs at all. `top:0` would drape blood across the brand on a page
        whose scripts are off, which is the failure dressed as a default.
        Asserted as a NUMBER greater than zero rather than as a literal, so
        a nav that genuinely changes height is a one-place edit.
        """
        block = _declaration_block(self._sheet(), f".{NAV_ANCHOR}")
        found = NAV_FALLBACK.search(block)

        self.assertIsNotNone(found, block)
        self.assertGreater(int(found.group(1)), 0)

    def test_the_nav_fallback_has_exactly_one_home(self, *_mocks):
        """The DRY half of AC 3, and the reason the hand uses a transform.

        Two elements hang from the ceiling and both need the nav cleared,
        which is the shape that invites the same number written twice. The
        upper handprint takes its extra drop from `translateY` instead of a
        second `top:calc(...)`, so the measurement's fallback appears once
        in the whole sheet. A test that had to keep two literals in step
        would be the sign the fact had two homes.

        Counted over the whole PAGE and not just the stylesheet, which is
        the only version of this test that works: an inline
        `top:calc(var(--navh,43px) + 60px)` on the handprint is exactly the
        duplicate being guarded against, and it would never appear in the
        sheet to be counted.
        """
        page = self.client.get(reverse("ui:home")).content.decode()

        self.assertEqual(len(NAV_FALLBACK.findall(page)), 1)

    def test_the_band_and_the_pool_scale_with_the_layer(self, *_mocks):
        """AC 12: a 420px ceiling on a 320px phone is most of the screen.

        These rungs are siblings of the stage, not children of it, which is
        why US-6.1's scale token had to move up to the container before this
        story could read it. Each asset names its full-size height and
        multiplies -- the token's fallback IS the full size, so there is no
        second copy of either number.
        """
        css = self._sheet()

        for selector, full in ((".blood svg", "420px"), (".pool svg", "62px"),
                               (".hand", "120px")):
            with self.subTest(selector=selector):
                block = _declaration_block(css, selector)
                self.assertIn(f"calc({full} * var(--decor-scale,1))", block)

    def test_the_token_lives_in_the_world_that_bleeds(self, *_mocks):
        """The token layer again: one world's colour, in one world's palette.

        NOT AC 9, for the reason its sibling above records -- AC 9 is the
        CONTRAST measurement, and the figures for it are in the story's
        Implementation notes rather than in any assertion here.

        The mockup's `--blood` is a four-world table because the mockup
        bleeds everywhere; this world is the only one that does, so the
        table collapses to one declaration. The third assertion is the one
        that keeps the arrangement honest: the base rules never READ the
        token, which is what lets it be a world-local property at all
        without `test_theme.py`'s universal scan demanding it from Manor,
        Arcade and Just the Work.
        """
        css = self._sheet()

        self.assertIn(BLOOD, _declaration_block(css, f".{HORROR}"))
        for world in (MANOR, CLEAN):
            with self.subTest(world=world):
                self.assertNotIn(BLOOD, _declaration_block(css, f".{world}"))
        self.assertNotIn(f"var({BLOOD})", _sections(css)["base"])

    def test_no_band_rule_forces_a_motion_property(self, *_mocks):
        """AC 10: REMOVE EFFECTS wins, and `!important` is how it would not.

        The stillness block uses `!important` precisely because a universal
        selector loses to a themed rule, so any rule here that reached for
        it too would be the one thing the switch could not withdraw. The
        version of this test in `test_decor.py` filters on selectors naming
        the container or the stage, so it never sees these.
        """
        for selector, block in CSS_RULE.findall(self._sheet()):
            if any(name in selector for name in RUNGS) or ".bd" in selector:
                with self.subTest(selector=selector.strip()):
                    self.assertNotIn("!important", block)
