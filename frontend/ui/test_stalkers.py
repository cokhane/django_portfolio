"""Tests for Found Footage's two stalkers and the strike each one leaves (US-6.7).

A separate module for the reason `test_decor.py`'s own docstring records: that
module sits at pylint's `too-many-lines` ceiling, and one module per story is
what this repo has done twelve times already. What stayed in `test_decor.py` is
what belongs to the STAGE -- the twelve slots on the shared clock, and the rule
that every child of the stage wears the gate of the cast that owns it. What is
here is what belongs to these four elements.

**The one thing this story could not inherit** is the pairing between a figure
and its blood. Every other property on this layer is a containment claim that a
shared rule already answers; `left` is ARITHMETIC, derived from where `stalk`
has carried the figure at the moment `strike` peaks. Derived values rot quietly
-- somebody retimes a keyframe and the splat goes on landing where nobody is
standing, with nothing red to show it -- so `test_the_strike_lands_where_the_
figure_was` recomputes it FROM THE STYLESHEET rather than from a copied number.
That test is the reason this module exists.

**What a Django render cannot carry is anything about motion.** It renders
templates, it does not run them. So the real gate for this story is the by-hand
pass in its Verification block: a whole 72-second cycle watched, a strike seen
to land, and 320px checked against the REMOVE EFFECTS cluster. These assertions
pin the things that CAN be read off the bytes and the sheet.
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, HORROR, MANOR, THEME_PARAM
from .test_chooser import _css
from .test_decor import CROSSING, DURATION, HORROR_CAST, STALKERS, STYLED_TAG, _element
from .test_effects import LAYER_ID
from .test_storm import _keyframes
from .test_theme import _declaration_block
from .tests import AVAILABILITY, PROJECTS, SKILLS

# The two slots US-6.1 cut and left empty, which this story fills. Each is taken
# TWICE -- once by a figure and once by its blood -- which is what makes a
# strike fire while its own figure is on screen rather than on a clock of its
# own. `test_decor.DELAYS` holds the whole grid; these are this story's share.
SLOTS = ("-56s", "-63s")

# What each element is allowed to say for itself, inline: its box and its slot.
# Everything else -- the world, the duration, the place the blood lands -- is a
# rule in the sheet. Keyed by (slot, name) rather than nested, because the four
# are one flat set of facts and the pairing IS the design: the taller figure
# leads on -56s and the smaller follows seven seconds later, each with a splat
# proportioned to it.
BOXES = {("-56s", "stalker"): "92px", ("-56s", "kill"): "150px",
         ("-63s", "stalker"): "78px", ("-63s", "kill"): "120px"}

# The figure's own tempo. 1.5s is the rule's, so the first figure says nothing;
# 1.9s is inline on the second, the same "a tempo is data" shape US-6.3's
# droplets use. Neither may be the shared clock -- a figure on 72s rocks once a
# minute -- which is what `DURATION` is imported to deny.
SWAY_RULE = "1.5s"
SWAY_INLINE = "1.9s"

# Half the widest splat (150px) at the 1000px width the mockup was drawn at.
# THE TOLERANCE IS THE CLAIM: a splat must overlap the ground the figure stood
# on, and half its own width is exactly that statement, expressed in the vw the
# travel arithmetic already works in. Not a round number chosen to make the
# current value pass -- the mockup's own second splat, at `left:38%`, is 11vw
# from the strike point and fails this, which is the error AC 6 is named for.
SPLAT_HALF_VW = 7.5

TRANSLATE_VW = re.compile(r"translateX\((-?[\d.]+)vw\)")
OPACITY = re.compile(r"opacity:([\d.]+)")
LEFT_PERCENT = re.compile(r"left:([\d.]+)%")
COLOUR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,6}|rgba?\(")


def _stops(body):
    """Every `(percent, declarations)` pair in a keyframes body, commas split.

    A stop may head several percentages at once -- `12.5%,100%{...}` -- and
    both of them carry the declarations that follow. Splitting them here is
    what lets the callers below treat a keyframe set as a plain list of
    (moment, state) readings rather than as text.
    """
    pairs = []
    for heads, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", body):
        for head in heads.split(","):
            pairs.append((float(head.strip().rstrip("%")), declarations))
    return pairs


def _strike_point(css):
    """Where the figure is, in vw, at the moment its strike peaks.

    THE WHOLE ARITHMETIC, read off the sheet rather than copied from it. The
    crossing interpolates `translateX` linearly from its first stop to the stop
    that reaches the far side; the strike peaks at whichever of its stops is
    most opaque. Position is the linear interpolation between them.

    Parsed rather than pinned because a pinned number cannot fail: the point of
    this value is that it MOVES when somebody retimes `stalk` or `strike`, and
    a test holding its own copy would go on agreeing with itself while the
    stylesheet walked away from it.
    """
    travel = [(percent, float(found.group(1)))
              for percent, declarations in _stops(_keyframes(css, "stalk"))
              if (found := TRANSLATE_VW.search(declarations))]
    start = min(travel)[1]
    end = max(vw for _percent, vw in travel)
    span = min(percent for percent, vw in travel if vw == end)

    lit = [(float(found.group(1)), percent)
           for percent, declarations in _stops(_keyframes(css, "strike"))
           if (found := OPACITY.search(declarations))]
    peak = max(lit)[1]
    return start + (peak / span) * (end - start)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class StalkerMarkupTests(SimpleTestCase):
    """The four elements as the server sends them, in every world."""

    def _layer(self, query=None):
        """The decoration layer's markup, from `<div id="decor"` to its close."""
        page = self.client.get(reverse("ui:home"), query or {}).content.decode()
        return _element(page, LAYER_ID)

    def test_each_figure_and_its_strike_share_one_slot(self, *_mocks):
        """AC 1: a strike fires while its own figure is crossing, not apart from it.

        The pairing is the assertion. A splat on a slot of its own would still
        appear every 72 seconds, still look correct in a screenshot, and still
        be wrong every time: it would fire with no figure there, which is the
        one thing blood on a floor cannot survive.

        Taken as a COUNT per slot rather than a presence check -- two elements
        at `-56s` and two at `-63s` -- because "a kill exists somewhere" passes
        just as happily when both splats have drifted onto one figure's slot.
        """
        layer = self._layer()

        for slot in SLOTS:
            taken = [classes for classes, style in STYLED_TAG.findall(layer)
                     if f"animation-delay:{slot}" in style]
            with self.subTest(slot=slot):
                self.assertEqual(len(taken), 2)
                self.assertEqual(sorted(names.split()[0] for names in taken),
                                 sorted(STALKERS))

    def test_only_the_box_and_the_slot_are_written_inline(self, *_mocks):
        """AC 4 and AC 6: what is data, and what is a rule the data leans on.

        Each element carries `--decor-size` and `animation-delay` and nothing
        else. The two absences are the ones worth testing. A `width:` would
        escape `--decor-scale` and ship a figure that does not shrink on a
        phone -- the mockup's `!important` phone rule is what that looks like.
        A `left:` on a splat would be the by-eye placement AC 6 forbids, and
        would also be the point at which the two splats could drift apart.
        """
        layer = self._layer()

        for (slot, name), box in BOXES.items():
            element = [style for classes, style in STYLED_TAG.findall(layer)
                       if name in classes.split() and f"animation-delay:{slot}" in style]
            with self.subTest(slot=slot, element=name):
                self.assertEqual(element, [f"--decor-size:{box}; animation-delay:{slot}"])

    def test_all_four_ship_in_every_world_and_are_withdrawn_by_the_stylesheet(self, *_mocks):
        """AC 8 and **F-18**: the server never knows the world.

        The world is a class the store puts on `<html>` in the browser, and the
        chooser swaps it live with no page load, so withdrawal is a stylesheet's
        job. The proof is that a render pinned to Manor -- or to Just the Work,
        the world defined by absence -- still carries all four in its bytes.

        The rules that do the withdrawing are NAMED here, not re-pinned:
        `:root:not(.horror) .horror-cast` is US-6.3's and is pinned in
        `test_found_footage.py`, `.clean #decor` and `.no-motion #decor` are
        US-6.1's and are pinned in `test_decor.py`. This story adds no gate of
        its own, and a second copy of someone else's assertion would only be
        one more thing to keep in step. What IS this story's to prove is that
        all four wear the class those rules reach.
        """
        for world in (MANOR, HORROR, CLEAN):
            layer = self._layer({THEME_PARAM: world})
            wearing = [classes for classes, _style in STYLED_TAG.findall(layer)
                       if set(classes.split()) & set(STALKERS)]
            with self.subTest(world=world):
                self.assertEqual(len(wearing), sum(STALKERS.values()))
                for classes in wearing:
                    self.assertEqual({HORROR_CAST, CROSSING} - set(classes.split()), set())


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class StalkerStylesheetTests(SimpleTestCase):
    """The rules the four elements are data against."""

    def _sheet(self):
        """The page's inline stylesheet."""
        return _css(self.client.get(reverse("ui:home")).content.decode())

    def test_the_strike_lands_where_the_figure_was(self, *_mocks):
        """AC 6: the one value on this layer that is arithmetic, not placement.

        `stalk` carries a figure across the viewport and `strike` fires partway
        through it. Because the two share a delay, the figure's position at the
        strike's peak is fully determined by the two keyframe sets -- and that
        position is where the blood belongs. Both splats take it: they peak at
        the same percentage of the same path, so there is ONE answer and one
        `left` in the sheet rather than two values placed by eye.

        Recomputed from the sheet every run, so retiming either keyframe set
        moves the expected answer and the sheet has to move with it. A copied
        constant would agree with itself forever.

        The splat is also asserted NOT to travel. `strike` scaling in place is
        what makes it blood on a floor; a `translateX` in it would make it a
        second figure, and it would drag the blood away from the spot this test
        just finished proving it belongs on.
        """
        css = self._sheet()
        expected = _strike_point(css)
        declared = _declaration_block(css, ".kill")

        self.assertNotIn("translateX", _keyframes(css, "strike"))
        self.assertIn("translateX", _keyframes(css, "stalk"))
        found = LEFT_PERCENT.search(declared)
        self.assertIsNotNone(found, ".kill declares no left -- the pairing is unasserted")
        self.assertAlmostEqual(float(found.group(1)), expected, delta=SPLAT_HALF_VW)

    def test_each_figure_sways_on_its_own_tempo_off_the_shared_clock(self, *_mocks):
        """AC 5: two tempos per figure, and the fast one is not the cycle.

        The crossing is slow and shared; the sway is the figure's own. Put the
        sway on the 72s clock and the figure rocks once a minute, which is the
        failure this asserts against rather than the tidiness it looks like.

        One tempo in the rule and one inline is deliberate, not an oversight:
        1.5s is what a sway IS, so the first figure says nothing, and the
        second overrides with data exactly as US-6.3's droplets do.
        """
        css = self._sheet()
        sway = _declaration_block(css, ".stalker .sway")

        self.assertIn(f"animation:sway {SWAY_RULE}", sway)
        self.assertNotIn(DURATION, sway)
        self.assertNotIn("transform-origin", sway)
        overrides = re.findall(rf'class="sway" style="animation-duration:{SWAY_INLINE}"',
                               _element(self.client.get(reverse("ui:home")).content.decode(),
                                        LAYER_ID))
        self.assertEqual(len(overrides), 1)

    def test_the_figures_own_rules_name_their_animation_and_no_geometry(self, *_mocks):
        """AC 2, AC 3 and AC 4: the three ways a crossing quietly stops working.

        `animation-duration` would be a second home for 72s. The `animation`
        SHORTHAND would declare `animation-duration:0s` by omission, which
        today loses to `#drift .crossing` on specificity and would tie the day
        anyone wrote `#drift .stalker{...}`. A `width:` would take the figure
        off `--decor-scale`. None of the three shows on screen until it does.

        `opacity` is asserted absent for a different reason: both keyframe sets
        drive it across the whole cycle, so a resting value is painted over at
        every moment the element exists and could only ever drift out of step
        with the stops that actually govern it.
        """
        css = self._sheet()

        for name in sorted(STALKERS):
            own = _declaration_block(css, f".{name}")
            with self.subTest(rule=name):
                self.assertIn("animation-name:", own)
                self.assertNotIn("animation:", own)
                self.assertNotIn("width:", own)
                self.assertNotIn("!important", own)
                self.assertNotIn("opacity", own)
                self.assertNotIn(DURATION, own)

    def test_the_figures_artwork_is_sized_by_the_stage_and_lit_by_its_own_rule(self, *_mocks):
        """AC 4: `.stalker svg` carries the one thing that is genuinely its own.

        `#drift svg` already sizes every creature on the stage, so repeating
        `width:100%` here is the per-element duplication US-6.1 was asked to
        drop -- and `test_decor.test_the_artwork_is_sized_by_one_rule_rather_
        than_six` pins the set of sizing rules at exactly three, so a fourth
        fails there rather than here. The drop-shadow is the exception: it is
        per-figure, and the phone widths drop it for free through
        `#decor *{filter:none}`.
        """
        own = _declaration_block(self._sheet(), ".stalker svg")

        self.assertIn("filter:drop-shadow", own)
        self.assertNotIn("width:", own)
        self.assertNotIn("display:", own)

    def test_the_splat_reaches_its_colour_only_through_this_world_s_token(self, *_mocks):
        """AC 7: the blood is `var(--blood)`, and no fallback stands behind it.

        A fallback would make the literal the real colour and the token a
        second name for it -- US-6.3 weighed that and wrote down why it loses.
        Gating these elements to the world that DECLARES `--blood` is what
        makes the no-fallback rule hold by construction: the splat cannot
        paint where its colour is undefined, because it cannot paint there.

        So the token's home is asserted too. If a later story widens the gate,
        this fails and sends the reader to US-6.3's instruction -- define it in
        all four worlds -- rather than to the fallback.
        """
        page = self.client.get(reverse("ui:home")).content.decode()
        splat = re.findall(r'<div class="kill[^"]*"[^>]*>(.*?)</div>',
                           _element(page, LAYER_ID), re.S)

        self.assertEqual(len(splat), STALKERS["kill"])
        for artwork in splat:
            self.assertIn('fill="var(--blood)"', artwork)
            self.assertEqual(COLOUR_LITERAL.findall(artwork), [])
        self.assertIn("--blood:", _declaration_block(self._sheet(), f".{HORROR}"))
