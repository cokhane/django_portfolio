"""Tests for the lightning storm and the power cut, and the two clocks they keep.

A separate module for the reason `test_found_footage.py` records: `test_decor.py`
is the full one -- it carries US-6.1's stage and US-6.2's cast, and this story's
one addition to it (a third SVG group) took it to within three lines of pylint's
`too-many-lines` ceiling. US-6.3's world went to its own module and US-6.4's
weather lands here. The story's Scope names `tests.py`, which is the API and view
suite; the per-story split is the newer decision and the one the repo follows.

**What this module does NOT re-assert.** Everything here lives inside `#decor`,
and containment is what makes the layer's existing guarantees cover it for free:
`test_decor.py` already walks the container on all three pages for anything
focusable or clickable, and `test_effects.py` already pins that ONE rule
withdraws the whole container for REMOVE EFFECTS and that the stylesheet reads no
OS motion preference. Both halves of AC 8 and AC 11 are therefore already owned,
and a second copy here would be one more thing to keep in step.

What is left is what is genuinely this story's: the two clocks and why they are
prime, the gate that names two worlds rather than one, the four rungs, the switch
each half answers to, and the promise that the escape control outranks the dark.
"""

import re
from math import gcd
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, HORROR, MANOR, THEME_PARAM
from .test_chooser import _css
from .test_decor import CROSSING, SCARE_HOOK, STYLED_TAG, WEATHER_CAST, _element
from .test_effects import LAYER_ID, _z
from .test_theme import _colour_literals, _declaration_block
from .tests import AVAILABILITY, PROJECTS, SKILLS

# The seven elements and how many of each. Written out because the COUNT is the
# decision: three pairs of eyes at three sizes read as a room with things in it,
# where one pair reads as a mascot. A seventh added without a rung would pass a
# count-free test.
WEATHER = {"storm": 1, "bolt": 1, "blackout": 1, "in-dark": 4}

# The ladder US-6.1 wrote before any of this existed, and the ceiling epic 6
# agreed to stay under.
RUNGS = {".storm": 440, ".bolt": 441, ".blackout": 450, ".in-dark": 455}

# US-5.5's cluster. The whole of F-17 is that this number is bigger than every
# number above, so the way out reads THROUGH the dark.
CONTROL_RUNG = 490

# The two clocks, and the only property of them that matters. They are PRIME, so
# they share no factor, so the pair returns to the same phase only every 247s.
STORM_CLOCK, POWER_CLOCK = 13, 19
REALIGNMENT = 247

# Which half of the story answers to the scares switch. The cut and what it
# reveals do; the lightning does not. The storm is weather and weather is
# ambient -- a visitor who turned scares off still gets the storm.
SCARED = ("blackout", "in-dark")
UNSCARED = ("storm", "bolt")

# The clock declared in a rung's own rule, e.g. `animation:storm 13s linear`.
CLOCK_SECONDS = re.compile(r"animation:\w+ (\d+)s")

# A width that is a number rather than the layer's token. The two drawn rungs
# read `--decor-size`, so the phone rules scale them with everything else.
FIXED_WIDTH = re.compile(r"width:\d")

# Every opacity a keyframe sets, as a number.
STOP_OPACITY = re.compile(r"opacity:(1|0|\.\d+)")

# The dark the cut settles at -- not its highest stop, which is a stutter.
SUSTAINED_DARK = 0.955


def _keyframes(css, name):
    """The body of `@keyframes name{...}`, nested braces and all.

    NOT `_declaration_block`, and the difference is not cosmetic. That helper
    ends at the first `}`, which in a keyframes block is the close of the
    FIRST STOP -- so it returns about twelve characters of a two-hundred
    character rule. A test asserting something is ABSENT from that slice
    passes whatever the rest of the rule says, which is the kind of green
    that is worse than red. This counts braces instead, so a stop can close
    without ending the block.
    """
    opening = f"@keyframes {name}{{"
    start = css.index(opening) + len(opening)
    depth, index = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(css[index], 0)
        index += 1
    return css[start:index - 1]


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class WeatherMarkupTests(SimpleTestCase):
    """What ships, what it wears, and what it refuses to carry."""

    def _layer(self, params=None):
        """The decoration layer's markup, for a world or for the default."""
        return _element(
            self.client.get(reverse("ui:home"), params or {}).content.decode(),
            LAYER_ID,
        )

    def test_the_whole_of_the_weather_is_in_the_layer(self, *_mocks):
        """AC 1 and AC 5: seven elements, and every one of them inside `#decor`.

        The count is asserted rather than mere presence, because the thing
        that breaks silently is an element added outside the container --
        it would render, it would look right, and it would survive REMOVE
        EFFECTS, Just the Work and reduced motion, all three of which this
        story answers by containment alone.
        """
        layer = self._layer()

        for element, count in WEATHER.items():
            with self.subTest(element=element):
                self.assertEqual(layer.count(f'class="{element} '), count)

    def test_every_element_wears_its_gate_and_rides_no_shared_clock(self, *_mocks):
        """AC 1 and AC 6: the two things an element's class list has to get right.

        The gate is a class, so wearing it IS the membership. One rule
        withdraws the lot, which holds only while every element wears the
        marker -- one that misses it is not withdrawn by Arcade, and renders
        a thunderstorm over a neon cabinet.

        `crossing` is asserted ABSENT in the same pass, because it is the
        same question about the same list: US-6.2 allocated the 72s cycle
        and this story claims no slot on it. Independent clocks are the
        entire subject here, so an element of this story riding the shared
        one would contradict the design rather than merely break it.

        What is NOT re-asserted is where these elements sit on that cycle.
        The scan this once pointed at -- `test_found_footage.py` looking for
        `-56s` and `-63s` across the whole layer -- went when US-6.7 drew the
        stalkers that claim both slots. The guarantee did not go with it:
        `test_decor.test_every_crossing_takes_a_slot_on_the_shared_clock`
        equates every `animation-delay` in the layer with `DELAYS`, so a
        weather element taking any slot fails there, which is the stronger
        check and still not this module's to copy.
        """
        layer = self._layer()

        for classes, _style in STYLED_TAG.findall(layer):
            names = classes.split()
            if any(element in names for element in WEATHER):
                with self.subTest(element=classes):
                    self.assertIn(WEATHER_CAST, names)
                    self.assertNotIn(CROSSING, names)
        self.assertEqual(layer.count(WEATHER_CAST), sum(WEATHER.values()))

    def test_the_cut_answers_to_the_scares_switch_and_the_lightning_does_not(self, *_mocks):
        """AC 7: the decision this story was asked to make, asserted both ways.

        A near-total blackout that reveals eyes is a scare by any honest
        reading, so it wears US-5.6's hook and `.no-scares` takes it.
        Lightning is weather, and weather is ambient: a visitor who turned
        scares off asked not to be startled, not for better conditions.

        Both directions are pinned because each failure is silent and they
        are opposite. The hook missing from the cut means a visitor who
        turned scares off loses the lights anyway; the hook added to the
        storm means turning scares off quietly takes the weather too.
        """
        layer = self._layer()

        for classes, _style in STYLED_TAG.findall(layer):
            names = classes.split()
            if any(e in names for e in SCARED):
                with self.subTest(scared=classes):
                    self.assertIn(SCARE_HOOK, names)
        for element in UNSCARED:
            with self.subTest(unscared=element):
                opening = layer[layer.index(f'class="{element} '):]
                self.assertNotIn(SCARE_HOOK, opening[:opening.index(">")].split())

    def test_the_drawn_rungs_are_sized_by_the_token_and_not_by_a_number(self, *_mocks):
        """AC 10: the phone rules reach these only through `--decor-size`.

        `#decor` sets `--decor-scale` to .6 at 560px and .5 at 400px, and one
        rule multiplies the two. A width written as a number would ignore
        both and put a 290px bolt across most of a 320px screen -- the
        mockup patches exactly that case with a `42vw !important` override,
        which this port does not need and does not carry.
        """
        layer = self._layer()

        for classes, style in STYLED_TAG.findall(layer):
            if WEATHER_CAST in classes.split():
                with self.subTest(element=classes):
                    self.assertIn("--decor-size:", style)
                    self.assertIsNone(FIXED_WIDTH.search(style))

    def test_the_artwork_smuggles_in_no_colour_of_its_own(self, *_mocks):
        """The token layer's rule, applied where a ported asset would break it.

        Lightning and eyes carry colour on the SHAPE, as `_bat.html` does,
        which keeps it out of the one thing `test_theme.py` scans: an inline
        `style=`. These are the only assets in the layer that belong to no
        world's palette, so they are also the easiest place to reach for a
        literal and call it theming.
        """
        self.assertEqual(_colour_literals(self._layer()), [])

    def test_the_weather_ships_in_every_world_and_the_stylesheet_withdraws_it(self, *_mocks):
        """F-18: the server sends one page, and CSS decides what it shows.

        A server-side test cannot assert that Arcade renders no lightning,
        because the markup it is handed is byte-identical in all four worlds
        -- that identity IS the contract. So this pins the half the server
        owns, and the gate test below pins the half the stylesheet owns.

        This is why AC 11's wording is not followed literally. It asks for a
        test that the markup is ABSENT under Just the Work; absent markup
        would break F-18, which `test_decor.py` pins directly. What the
        story means by it is that nothing RENDERS there, and that is the
        gate's job, asserted below and twice over by `.clean #decor`.
        """
        for world in (MANOR, HORROR, CLEAN):
            with self.subTest(world=world):
                layer = self._layer({THEME_PARAM: world})
                self.assertIn(f'class="storm {WEATHER_CAST}"', layer)
                self.assertIn(f'class="blackout {WEATHER_CAST} {SCARE_HOOK}"', layer)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class WeatherStylesheetTests(SimpleTestCase):
    """The gate, the rungs, the clocks, and the promise about the way out."""

    def _sheet(self):
        """The stylesheet, comments stripped."""
        return _css(self.client.get(reverse("ui:home")).content.decode())

    def test_one_rule_withdraws_the_weather_from_the_two_worlds_without_it(self, *_mocks):
        """AC 6: the gate is a rule, and it is the only one.

        The shape both casts before it proved, with one difference: it names
        TWO worlds, so Arcade and Just the Work are the complement rather
        than a list. `:not()` is the only form that reaches Arcade at all --
        its root class is the empty string, so there is no `.arcade` to
        write a rule against.

        Asserted as the only rule mentioning the class, because a SECOND
        gate is how a per-element list grows back: one rule here, and an
        element joins the gate by wearing the marker.
        """
        css = self._sheet()
        gating = [selector for selector in css.split("{")
                  if WEATHER_CAST in selector and ":not(" in selector]

        self.assertEqual(len(gating), 1)
        self.assertIn(f":root:not(.{MANOR}):not(.{HORROR}) .{WEATHER_CAST}", css)
        self.assertIn("display:none", _declaration_block(
            css, f":root:not(.{MANOR}):not(.{HORROR}) .{WEATHER_CAST}"))

    def test_each_rung_takes_the_number_the_ladder_allocated(self, *_mocks):
        """AC 3: 440, 441, 450 and 455, written into the ladder before this story.

        Checked against US-6.1's table rather than merely against each
        other, so a rung quietly promoted above the glass fails here instead
        of in a browser.
        """
        css = self._sheet()

        for selector, rung in RUNGS.items():
            with self.subTest(selector=selector):
                self.assertEqual(_z(css, selector), rung)

    def test_the_way_out_outranks_the_dark(self, *_mocks):
        """AC 3 and **F-17**: the escape control stays reachable in a blackout.

        The one acceptance criterion that cannot be fully asserted from
        markup -- whether a human can FIND it is a by-hand check, recorded
        in the story's Implementation notes. What is mechanical is the half
        underneath it: every rung this story adds sits below US-5.5's
        cluster, so the control paints over the dark rather than under it.

        Derived from the rungs rather than from a literal 455, so a rung
        added later is covered by the same assertion.
        """
        css = self._sheet()

        self.assertEqual(_z(css, "#site-controls"), CONTROL_RUNG)
        for selector in RUNGS:
            with self.subTest(selector=selector):
                self.assertLess(_z(css, selector), CONTROL_RUNG)

    def test_the_two_clocks_are_prime_and_therefore_never_settle(self, *_mocks):
        """AC 1 and AC 2: 13 and 19, and the 247 seconds that follow from them.

        The arithmetic IS the feature, so it is asserted rather than trusted
        to a comment: two coprime periods return to the same phase only at
        their product. Tidied to 15 and 20 the pair would realign every 60s,
        four times as often, and the page would start to feel scheduled --
        which is the one thing the story exists to prevent.

        The primality is asserted directly because `gcd == 1` alone is
        weaker than the design: 13 and 18 are also coprime, but 18 shares
        factors with the mist's and the droplets' clocks. Primes are
        coprime with everything they do not divide, which is what makes
        these two safe against clocks that do not exist yet.
        """
        css = self._sheet()

        for selector, clock in ((".storm", STORM_CLOCK), (".bolt", STORM_CLOCK),
                                (".blackout", POWER_CLOCK), (".in-dark", POWER_CLOCK)):
            with self.subTest(selector=selector):
                found = CLOCK_SECONDS.search(_declaration_block(css, selector))
                self.assertIsNotNone(found)
                self.assertEqual(int(found.group(1)), clock)
        self.assertEqual(gcd(STORM_CLOCK, POWER_CLOCK), 1)
        self.assertEqual(STORM_CLOCK * POWER_CLOCK, REALIGNMENT)
        for clock in (STORM_CLOCK, POWER_CLOCK):
            with self.subTest(clock=clock):
                self.assertFalse(any(clock % n == 0 for n in range(2, clock)))

    def test_the_dark_is_near_total_and_never_total(self, *_mocks):
        """AC 4: the page keeps a trace of itself, at every stop and not just one.

        A full blackout on a site whose job is showing a portfolio is a few
        seconds of nothing, and it is also what hides the way out. `.955` is
        the whole of F-17's margin -- the control is legible through it and
        the page behind it is still faintly there.

        TWO assertions, because the first version of this test conflated
        them and was wrong. The SUSTAINED dark is `.955`, and that is the
        number F-17 rests on. But it is not the highest stop in the rule:
        the stutter on the way down peaks at `.96` for about a tenth of a
        second. So "near-total" is asserted where it is load-bearing, and
        "never total" is asserted across EVERY stop -- which is the claim
        that actually matters, since a single `opacity:1` anywhere in the
        cycle would black the page out completely, however briefly.
        """
        cut = _keyframes(self._sheet(), "powercut")
        stops = [float(stop) for stop in STOP_OPACITY.findall(cut)]

        self.assertIn(SUSTAINED_DARK, stops)
        self.assertLess(max(stops), 1)

    def test_the_weather_moves_nothing_a_phone_has_to_repaint(self, *_mocks):
        """AC 9: four infinite full-viewport animations, and all of them cheap.

        `opacity` is a compositor property; `background-color` is not.
        Animating the colour instead would repaint the whole viewport every
        frame for as long as the page is open, which on a phone is the
        difference between a decoration and a warm device.

        Asserted over the keyframes rather than over the rules, because the
        rules legitimately SET a background -- it is the static half. What
        must never appear is a background inside a keyframe.
        """
        css = self._sheet()

        for keyframes in ("storm", "bolt", "powercut", "revealed"):
            with self.subTest(keyframes=keyframes):
                block = _keyframes(css, keyframes)
                self.assertIn("opacity:", block)
                for banned in ("background", "filter:", "box-shadow"):
                    self.assertNotIn(banned, block)
