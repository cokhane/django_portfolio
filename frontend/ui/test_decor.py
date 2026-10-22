"""Tests for the stage epic 6's decoration is built on, and its 72-second clock.

A separate module for the reason `test_theme.py`, `test_hire_me_panel.py`,
`test_preferences.py`, `test_chooser.py`, `test_effects.py` and
`test_scares.py` each record: `tests.py` is already near pylint's
`too-many-lines` ceiling. The story's Scope names `tests.py` because it was
written before that split; the split is the newer decision and the one the
repo follows.

**Two stories live here, in that order.** US-6.1 built the STAGE and the
classes below pin it first; US-6.2 put Haunted Manor's CAST on it, and
`ManorCastMarkupTests` and `ManorCastStylesheetTests` pin that. The stage
tests were deliberately written against an empty layer -- the fence before
the thing it fences -- which is why several of them read as near-trivial and
are not: the cast was built inside boundaries that were already enforced.

What the stage pins:

1. **The container cannot take a click or a focus** (**NFR-8**, **F-14**).
2. **The container is NOT a stacking context**, which is the one property the
   whole ladder rests on and the one nothing on screen would show.
3. **The cycle is written once** -- one duration, in one rule (**AC 11**).
4. **Both switches withdraw the layer whole**, and the world defined by
   absence never renders it (**S11**).

What the cast adds: its count and its slots on that cycle, the world gate it
wears, the two tempos per creature and the pins they rotate about, and the
single shared body behind the two ghosts.

**What a Django render cannot carry is anything about motion**: it renders
templates, it does not run them. So the things that only a browser can show
were measured in one -- that every crossing resolves to 72000ms while a wing
beats at 260ms, that no creature intercepts a tap, and that nothing overflows
at 320px. Those numbers are recorded in US-6.2's Implementation notes, with
the occupancy counts behind **AC 2**.
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, MANOR, THEME_PARAM
from .test_chooser import CHOOSER_MARKER, _css, _open_tag
from .test_effects import LAYER_ID, STILL_CLASS, Z_INDEX, _z
from .test_preferences import (
    _assert_work_survives_without_scripts,
    _inline_script,
    _owned_script,
    _render_every_page,
    _without_scripts,
)
from .test_theme import CSS_RULE, _declaration_block
from .tests import AVAILABILITY, PROJECTS, SKILLS

# The z-0 stage inside the container, and the wrapper that lifts the work off
# it. Two elements rather than one because a `position:fixed` box forms a
# stacking context whatever its `z-index`: a single fixed container would rank
# every rung of the ladder at its own level, and 6.4's blackout would paint
# under the page it exists to black out.
STAGE_ID = "drift"
WRAPPER_ID = "page"

# The shared duration, as the stylesheet writes it. A crossing's visible window
# is a keyframe PERCENTAGE of this -- 19.5%, or 14.04s -- which is why one
# duration in one rule is the whole contract and nine inline copies would not be.
DURATION = "72s"
CYCLE = f"animation-duration:{DURATION}"

# US-5.5's Q2 recorded this: epic 6 stays under 455, and the four values above
# it are not epic 6's to use -- the vignette and scanlines it lowered to 488/489
# so its own cluster at 490 reads through them, and US-5.4's dialog at 500.
CEILING = 455
NOT_EPIC_SIX = (488, 489, 490, 500)

# The two phone widths and the scale each sets, from the plan's Responsive note.
SCALES = (("560px", "--decor-scale:.6"), ("400px", "--decor-scale:.5"))

# Any of these on the container would re-form the stacking context the ladder
# depends on not existing.
CONTEXT_FORMING = ("position", "z-index", "transform", "opacity", "filter")

REVEAL = f"{LAYER_ID}.hidden = false"

# `<div …>` and `</div>`, the two tags the walk below counts.
DIV = re.compile(r"<div\b|</div>")


# US-6.2's cast, and how many of each the stage carries. Written out because
# the number IS the decision: the mockup's nine delay slots are split across
# worlds, and Manor's seven crossings are the seven this names. A creature
# added without a slot would pass a count-free test and break the stagger.
CAST = {"ghost": 2, "bat": 2, "witch": 1, "ufo": 1, "alien": 1, "pumpkin": 4}

# The class every Manor element carries, and the one rule that withdraws
# them. One class rather than a selector list, so a creature added later is
# gated by wearing it rather than by somebody remembering a rule.
MANOR_CAST = "manor-cast"

# US-6.3's equivalent, named here because this module's svg-sizing test counts
# the layer's GROUP rules and there are now two groups on it.
HORROR_CAST = "horror-cast"

# US-5.6 built this as the ONE container every scare element lives in, and
# `.no-scares .scare{display:none}` already withdraws it. The approaching
# ghost joins that container rather than getting a rule of its own, so this
# story adds no selector to US-5.6's block -- its contract, line 3. The
# count of those rules stays test_scares.py's to assert.
SCARE_HOOK = "scare"
WORLD_GATE = f":root:not(.{MANOR}) .{MANOR_CAST}"

# The slow clock's subscribers, and Manor's delays on it -- seven creatures
# plus the beam, which rides the saucer's slot to run its own envelope.
# 7s apart, leaving 56 and 63 FREE -- US-6.3 was expected to take them and
# does not: its band, pool and hands each run their own clock. In the mockup
# the two slots belong to Found Footage's stalkers, which no story has claimed.
CROSSING = "crossing"

# An element that is DATA against a shared rule: it carries both a class list
# and an inline style. Matched so the crossing-timer test below can ask the
# question it is actually named for -- "does a CROSSING carry its own
# duration" -- rather than "does the layer contain the string anywhere",
# which was the same question only while every animated element on the layer
# was a crossing. US-6.3's droplets each carry their own tempo BY DESIGN.
#
# ORDER-DEPENDENT: `class` must precede `style`, which is how every element in
# this layer is written. That is a real limitation rather than an oversight,
# and the caller pays for it by pinning the COUNT of what it matches against
# `DELAYS` -- an element written the other way round drops the count and fails
# there, which a bare "did we match anything" guard would not have caught.
STYLED_TAG = re.compile(r'<\w+ class="([^"]*)" style="([^"]*)"')
DELAYS = ("0s", "-14s", "-21s", "-28s", "-35s", "-42s", "-49s", "-49s")

# The articulated parts and the pin each rotates about, in the SVG's own
# coordinate space. Ported without these, wings and cloak rotate about the
# element corner and the creature visibly breaks.
PINS = {".bat .wing": "transform-origin:60px 24px", ".witch .cloak": "transform-origin:118px 40px"}

# A creature's own fast tempo. None of these may be the shared 72s: the
# mockup beats a wing at .26s and bills a cloak at 1.8s, and putting either
# on the slow clock produces a bat that flaps once a minute.
TEMPOS = ("animation:flap .26s", "animation:billow 1.8s", "animation:gutter 2.6s",
          "animation:bob 4.6s", "animation:waft 19s")

# The rung mist takes, and the one it must not: `#drift` is a stacking
# context at z-index 0, so mist inside it could never paint above the work.
MIST_ID = "mist"

# The classes a cast element wears that say WHAT IT DOES rather than what it
# IS -- its world, its subscription to the clock, its scare binding, its bob
# wrapper. Subtracted from an element's class list, what remains is the
# creature's own name, which is how the crossing selectors below are DERIVED
# from the markup instead of being a third hand-kept copy of the cast.
STRUCTURAL = frozenset({CROSSING, MANOR_CAST, SCARE_HOOK, "bob"})

# A rule that styles a creature ITSELF rather than a part inside it: all
# classes, no descendant. `.ghost` and `.ghost.approach` qualify; `.bat .wing`
# and `.bat svg` are parts, and parts legitimately own a fast tempo written
# with the `animation` shorthand. The name is matched with a WORD BOUNDARY:
# a plain substring test lets a rule renamed `.beamX` satisfy a search for
# `.beam`, so a creature whose rule was renamed away still reads as covered.
OWN_RULE = re.compile(r"^\.[\w.-]+$")

ANY_KEYFRAME = re.compile(r"@keyframes\s+([a-z-]+)")

# The highlight in a ghost's eye -- present on the drifting one, absent on
# the one that notices you, and the ONLY way the two differ.
GLINT = re.compile(r'<ellipse cx="\d+" cy="36"[^>]*opacity="\.55"/>')


def _element(html, element_id):
    """The markup of `#element_id`, from its own `<div` to its matching close.

    A depth walk rather than a slice up to whatever happens to come next,
    because the question these tests ask is CONTAINMENT and a slice cannot
    answer it. "Is the layer outside the wrapper" asked as "is there a
    `</div>` between them" is satisfied by any one of the dozens inside the
    content, so it passes whether the layer is in or out -- which is the one
    arrangement it exists to catch.
    """
    start = html.rindex("<div", 0, html.index(f'id="{element_id}"'))
    depth = 0
    for tag in DIV.finditer(html, start):
        depth += 1 if tag.group().startswith("<div") else -1
        if depth == 0:
            return html[start:tag.end()]
    raise AssertionError(f"#{element_id} is never closed")


def _media_block(css, query):
    """The declarations inside `@media <query>{...}`, matched by brace depth.

    A slice running from the query to the END of the stylesheet is not the
    same thing, and the difference is a test that cannot fail. A rule moved
    OUT of the media query but written after it still falls inside such a
    slice -- so "filters are dropped at phone width" would read exactly the
    same as "filters are dropped at every width", which is a different and
    much worse change.
    """
    opening = f"@media {query}{{"
    start = css.rindex(opening) + len(opening)
    depth = 1
    for index in range(start, len(css)):
        depth += {"{": 1, "}": -1}.get(css[index], 0)
        if depth == 0:
            return css[start:index]
    raise AssertionError(f"@media {query} is never closed")


def _crossing_names(layer):
    """Every creature class worn by something that takes the shared clock.

    DERIVED from the rendered layer rather than listed, and the difference is
    the whole value: a hand-kept tuple would leave the NEXT crossing unguarded
    by the test that claims to guard the cycle -- silently, and in a story
    that cannot fail yet. Anything wearing `crossing` is covered the day it is
    written, whether that is US-6.4's weather or whoever finally draws the
    stalkers the mockup leaves in slots 56 and 63. (US-6.3 was expected to be
    that story and was not: Found Footage's band runs its own clocks and puts
    nothing on this one.)

    Scanned over the whole layer, not just the stage's direct children: the
    saucer's beam is a GRANDCHILD, and it takes the clock too.
    """
    names = set()
    for classes in re.findall(r'class="([^"]*\bcrossing\b[^"]*)"', layer):
        names |= set(classes.split()) - STRUCTURAL
    return names


def _stage_children(stage):
    """The `class` of every DIRECT child of `stage`, grandchildren excluded.

    A flat regex over the same markup also finds the ghosts' `.bob` wrappers
    and the saucer's beam, so a count taken that way reports fourteen
    elements on an eleven-creature stage -- and, worse, a missing class on a
    grandchild that was never required to carry one would read as a failure.
    Depth is the only honest way to ask what is ON the stage.
    """
    classes, depth = [], 0
    for tag in re.finditer(r"<div\b[^>]*>|</div>", stage):
        if tag.group().startswith("</"):
            depth -= 1
            continue
        if depth == 1:
            found = re.search(r'class="([^"]+)"', tag.group())
            classes.append(found.group(1) if found else "")
        depth += 1
    return classes


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class DecorLayerMarkupTests(SimpleTestCase):
    """What the server actually sends, on every page a visitor can reach."""

    def _page(self, query=None):
        """The home page's HTML, optionally pinned to a world."""
        return self.client.get(reverse("ui:home"), query or {}).content.decode()

    def test_the_layer_ships_hidden_and_unseen_by_a_reader_on_every_page(self, *_mocks):
        """AC 1: one container, on all three pages, announced to nobody.

        `aria-hidden` is **F-14**: a screen reader naming a bat between two
        case studies is the failure the attribute exists to prevent, and the
        layer has no text, so there is nothing for a reader to lose.

        `hidden` in the bytes the server sends is US-5.5's contract, and its
        reason is not this story's: the OS reduced-motion preference reaches
        the page only through the store, in script, because the stylesheet
        deliberately holds no `prefers-reduced-motion` query. Shipping the
        layer hidden is what makes a visitor with scripts off a still site by
        construction rather than one that ignores their system setting.

        Asserted per page because `base.html` has three renderers and one of
        them is not ours -- Django's own `page_not_found`. A layer wired into
        a view would be absent exactly there.
        """
        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                tag = _open_tag(html, LAYER_ID)
                self.assertIn('aria-hidden="true"', tag)
                self.assertIn(" hidden>", tag)
                self.assertIn(f'id="{STAGE_ID}"', html)

    def test_nothing_in_the_layer_can_take_a_click_or_a_focus(self, *_mocks):
        """AC 2 (**NFR-8**): the fence, built while there is nothing behind it.

        Written by US-6.1 against an EMPTY stage, which was the point: the
        fence goes up before the thing it fences, so the first creature is
        built inside a boundary already enforced rather than against one
        somebody has to remember. A decorative shape that swallows a tap is a
        dead patch over work a visitor is reaching for, and on a phone it is
        a tap that simply does nothing.

        `pointer-events` is asserted absent from the markup as well as set on
        the container in CSS: the container's rule cannot protect the page
        from a child that re-enables pointers on itself.

        US-6.2 then populated it, and this is where that is cashed in:
        eleven elements and ~7.4KB of markup later, the layer
        still announces nothing and still swallows no tap. `role=` joined
        the list then, because an SVG given one would be announced even
        under `aria-hidden`. Run over all three pages for the reason the
        test above records.
        """
        for name, html in _render_every_page(self.client).items():
            layer = _element(html, LAYER_ID)
            for focusable in ("<a", "<button", "tabindex", "pointer-events", "role="):
                with self.subTest(page=name, focusable=focusable):
                    self.assertNotIn(focusable, layer)

    def test_the_work_is_wrapped_and_the_layer_sits_outside_the_wrapper(self, *_mocks):
        """AC 5 and flag **F12**: what lifts the content, and what it does not contain.

        The mockup lifts its content with `.wrap{position:relative; z-index:1}`
        and this codebase never had it -- Tailwind gives each section its own
        gutter, so there was no shared wrapper to carry the rule. Without one
        the content is unpositioned, and an unpositioned box paints BELOW a
        positioned one at `z-index:0`, so the decoration would cover the
        portfolio rather than sit behind it.

        The layer must then close OUTSIDE that wrapper, which is the half
        **F12** is about: inside it, the layer would inherit the wrapper's
        stacking context and a swap of the content could disturb it.
        """
        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                self.assertLess(
                    html.index(f'id="{WRAPPER_ID}"'), html.index(f'id="{LAYER_ID}"')
                )
                self.assertNotIn(f'id="{LAYER_ID}"', _element(html, WRAPPER_ID))

    def test_the_page_reads_without_the_layer(self, *_mocks):
        """**A1**: the work survives the visitor who cannot run the scripts.

        This story adds a fourth fixed, always-on-screen element to every
        page, which is the kind of addition that quietly takes a site away
        from someone who cannot dismiss what floats over it. Here the layer is
        not merely dismissible -- without scripts it is never revealed at all.
        """
        _assert_work_survives_without_scripts(self, _without_scripts(self._page()))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class DecorRevealTests(SimpleTestCase):
    """Which script reveals the layer, and which one must not."""

    def test_the_layer_is_revealed_by_the_script_that_owns_the_controls(self, *_mocks):
        """AC 1: revealed at the end of `<body>`, never from `<head>`.

        The head script's single job is to be right BEFORE the browser paints,
        and it runs where this element does not exist yet -- `getElementById`
        there returns null and the page dies on the next line. The reveal
        belongs with the chooser and the control cluster, which are revealed
        for their own reason and in the same place.

        Unconditional, deliberately. The reveal does not consult the store:
        the stillness class is already on `<html>` by this point if it belongs
        there, and the stylesheet withdraws the layer from under it. A second
        gate in script would be a second answer to the same question.
        """
        html = self.client.get(reverse("ui:home")).content.decode()

        self.assertIn(REVEAL, _inline_script(html, CHOOSER_MARKER))
        self.assertNotIn(REVEAL, _owned_script(html))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class DecorStylesheetTests(SimpleTestCase):
    """The ladder, the clock and the two switches that withdraw them."""

    def _sheet(self, query=None):
        """The stylesheet, comments stripped, optionally from a pinned world."""
        return _css(self.client.get(reverse("ui:home"), query or {}).content.decode())

    def test_the_container_is_not_a_stacking_context(self, *_mocks):
        """AC 5, and the single property the whole ladder rests on.

        A `position:fixed` box forms a stacking context whatever its
        `z-index`, and a child of one can never outrank it. So a container
        that positioned itself would rank every rung inside it at its own
        level: 6.3's blood band and 6.4's blackout would both paint beneath
        the page content at `1`, and a power cut would black out nothing.

        The container therefore carries exactly one declaration -- the one
        **NFR-8** asks for, inherited by every rung inside it. `position`,
        `z-index`, `transform`, `opacity` and `filter` each re-form the
        context, so each is asserted absent rather than merely left out. This
        is invisible on screen and silent in review, which is why it is a
        test and not a comment.
        """
        block = _declaration_block(self._sheet(), f"#{LAYER_ID}")

        self.assertIn("pointer-events:none", block)
        for forming in CONTEXT_FORMING:
            with self.subTest(declaration=forming):
                self.assertNotIn(f"{forming}:", block)

    def test_the_stage_is_fixed_and_clips_what_crosses_it(self, *_mocks):
        """AC 1 and AC 10: the rung this story ships, and why it clips.

        `overflow:hidden` is not decoration. A crossing travels to `118vw` by
        the end of its window, and the stage is what stops that becoming
        horizontal scroll on a phone -- the half of AC 10 a stylesheet can
        carry on its own.
        """
        block = _declaration_block(self._sheet(), f"#{STAGE_ID}")

        for declaration in ("position:fixed", "inset:0", "overflow:hidden"):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, block)

    def test_the_work_is_lifted_above_the_stage_and_below_the_glass(self, *_mocks):
        """AC 5: the bottom of the ladder, pinned as an ORDER not as numbers.

        Asserted with `<` rather than against `0` and `1`, for the reason
        `test_effects.py` records about the top of the same ladder: retuning
        it stays a free change, and INVERTING it fails. Inverted is the only
        way to get it wrong -- content under the ghosts is a portfolio behind
        a bat.
        """
        css = self._sheet()

        self.assertLess(_z(css, f"#{STAGE_ID}"), _z(css, f"#{WRAPPER_ID}"))
        self.assertLess(_z(css, f"#{WRAPPER_ID}"), _z(css, "body::after"))

    def test_nothing_in_the_stylesheet_climbs_past_the_ceiling(self, *_mocks):
        """AC 5: the ceiling as a SCAN, so 6.2 to 6.5 are bound without a list.

        US-5.5 set epic 6's ceiling at 455 -- not the 490 the mockup's table
        shows, which is the control cluster's own value. Above the ceiling sit
        four rungs that are not epic 6's to take: the vignette and scanlines
        it lowered to 488/489 so the cluster reads through them, the cluster
        at 490, and US-5.4's dialog at 500. **F-17** -- the way out is
        reachable DURING a scare -- is exactly this inequality.

        Scanned over every rule in the stylesheet rather than over the rules
        whose selector names the layer, and that is deliberate: a rung is a
        CHILD of the container in the markup, so 6.3's `.blood` and 6.4's
        `.blackout` will not name it in CSS. A scan that trusted the selector
        would pass while the thing it guards walked straight past it.
        """
        for selector, block in CSS_RULE.findall(self._sheet()):
            found = Z_INDEX.search(block)
            if found is None:
                continue
            value = int(found.group(1))
            with self.subTest(selector=selector.strip()):
                self.assertTrue(
                    value <= CEILING or value in NOT_EPIC_SIX,
                    f"z-index {value} is above epic 6's ceiling of {CEILING}",
                )

    def test_the_cycle_is_written_once(self, *_mocks):
        """AC 3 and AC 11: one duration, in one rule, for the whole cast.

        The mockup repeats `animation-duration:72s` inline on all nine of its
        crossings. That is the duplication AC 11 forbids, and it is not
        cosmetic: a crossing's visible window is a keyframe PERCENTAGE of the
        duration -- 19.5%, which is 14.04s only while the duration is 72s --
        so nine copies are nine chances for one creature's window to stop
        meaning 14 seconds. Written once, retiming the cast is one edit.

        The count is taken over the comment-stripped stylesheet, so the prose
        above the rule explaining the number cannot satisfy the assertion.

        What stays per-creature is the DELAY, and it stays inline as data:
        nine different values cannot be one rule, and US-5.5's contract
        already anticipated them ("inline `animation-delay` attributes
        included"). A delay in the stylesheet would be a creature's identity
        written somewhere other than the creature.
        """
        css = self._sheet()

        self.assertIn(CYCLE, _declaration_block(css, f"#{STAGE_ID} .crossing"))
        self.assertEqual(css.count(DURATION), 1)
        self.assertNotIn("animation-delay", css)

    def test_the_cast_scales_down_twice_at_phone_width(self, *_mocks):
        """AC 10: two breakpoints, one token, no per-creature list.

        The mockup shrinks eleven creatures with eleven `!important` widths at
        560px and six more at 400px. One token the LAYER redefines does the
        same job, and a creature that arrives later is scaled without anyone
        editing a media block. On the layer and not the stage because the
        rungs above `#drift` -- US-6.3's blood, pool and hands -- are its
        SIBLINGS: a token declared on the stage reaches the cast and misses
        every one of them. The stage still READS it; it just no longer owns it.

        Read through `_media_block`, which matches braces. This test used to
        slice from the last `560px` query to the END of the sheet, which
        cannot fail: a scale rule moved OUT of the query would still fall
        inside the slice. The chooser owns an earlier `560px` block of its
        own, which is why the helper takes the last. Size is read as
        `var(--decor-scale,1)` and the token is declared nowhere else, so the
        fallback IS the full-size default and there is no second copy to
        drift from this one.
        """
        css = self._sheet()

        for width, scale in SCALES:
            with self.subTest(width=width):
                block = _media_block(css, f"(max-width:{width})")
                self.assertIn(scale, _declaration_block(block, f"#{LAYER_ID}"))
        self.assertIn("var(--decor-scale,1)", _declaration_block(css, f"#{STAGE_ID} > *"))

    def test_both_switches_withdraw_the_whole_layer(self, *_mocks):
        """AC 6 and AC 7: one selector each, and the layer goes entire.

        `display:none` on the CONTAINER, not on anything inside it. It cancels
        the animations rather than painting over them, which is what makes
        stillness genuinely cheaper on a weak device, and it needs no second
        line the day 6.4 adds a rung -- the rung is inside the container.
        That one-line cost is what US-5.5's contract licensed, and
        `test_effects.py` counts its block to keep it at one.

        **AC 8 is this same rule.** The stylesheet holds no
        `prefers-reduced-motion` query -- `test_effects.py` pins that absence
        -- because the store reads the system preference once and expresses it
        as the stillness class. So a visitor who asked their system for calm
        gets the layer ABSENT, not frozen: decided, and recorded in the
        story. 6.2 must not port the mockup's frozen-creature opacities;
        under `display:none` they would style nothing.

        Just the Work is the same shape for a different reason -- **S11**
        defines that world by absence, and a calmer bat is still a bat. In CSS
        rather than script because a world swaps live through the chooser: the
        rule re-reads on the frame the root class changes.
        """
        css = self._sheet()

        for prefix in (f".{STILL_CLASS}", f".{CLEAN}"):
            with self.subTest(prefix=prefix):
                self.assertIn(
                    "display:none", _declaration_block(css, f"{prefix} #{LAYER_ID}")
                )

    def test_the_layer_forces_no_motion_property(self, *_mocks):
        """AC 8 and US-5.5's contract line 3: `!important` is never written here.

        The stillness class works by a blanket `animation:none !important` on
        everything. `!important` on a motion property inside the layer is the
        one thing that would survive it -- the two declarations would tie on
        weight and source order would decide, which is not a rule anyone
        should have to reason about to know whether a visitor's preference
        holds. So the layer writes none at all, anywhere, and 6.2 to 6.5
        inherit that.
        """
        for selector, block in CSS_RULE.findall(self._sheet()):
            if LAYER_ID not in selector and STAGE_ID not in selector:
                continue
            with self.subTest(selector=selector.strip()):
                self.assertNotIn("!important", block)

    def test_just_the_work_still_ships_the_same_document(self, *_mocks):
        """AC 6 and **F-18**: a world withdraws the layer; it does not rewrite it.

        The markup is identical in every world, because the world is a class
        the store puts on `<html>` in the browser -- the server cannot know it
        and must not guess. Withdrawal is therefore a stylesheet's job, and
        the proof is that the element is still in the bytes a `?theme=clean`
        render sends.
        """
        pinned = self.client.get(reverse("ui:home"), {THEME_PARAM: CLEAN})

        self.assertIn(f'id="{LAYER_ID}"', pinned.content.decode())

    def test_a_category_swap_carries_no_decoration(self, *_mocks):
        """AC 9 (flag **F12**): the layer cannot be duplicated by a swap.

        Structural rather than careful: the layer lives in `base.html` outside
        `#grid`, and the partial a swap fetches does not extend `base.html` at
        all, so there is no path by which a second copy could arrive. The
        assertion pins that the partial stays standalone -- the day somebody
        makes it extend the base template, every HTMX swap would inject a
        second decoration layer and a second copy of the stylesheet.
        """
        partial = self.client.get(reverse("ui:project-grid")).content.decode()

        for absent in (f'id="{LAYER_ID}"', f'id="{WRAPPER_ID}"', "<style"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, partial)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ManorCastMarkupTests(SimpleTestCase):
    """The cast US-6.2 puts on US-6.1's stage, as the server sends it."""

    def _layer(self, query=None):
        """The decoration layer's markup, from `<div id="decor"` to its close."""
        page = self.client.get(reverse("ui:home"), query or {}).content.decode()
        return _element(page, LAYER_ID)

    def test_the_whole_cast_is_on_the_stage(self, *_mocks):
        """AC 1: eleven elements, and the COUNT of each is the assertion.

        Counting rather than merely finding one of each is what makes this a
        test of the decision instead of a test of the markup's existence.
        The cast size was a question the story asked out loud -- nine is the
        plan's number, a smaller cut was explicitly allowed -- and the answer
        is bound to the stagger: Manor holds seven of the mockup's nine delay
        slots and leaves two free. A creature added without a slot
        reads as clutter and a creature dropped leaves the stage bare, and
        neither shows up in a test that only asks "is there a bat".
        """
        layer = self._layer()

        for creature, expected in CAST.items():
            with self.subTest(creature=creature):
                self.assertEqual(len(re.findall(rf'class="{creature}\b', layer)), expected)

    def test_no_creature_carries_its_own_crossing_timer(self, *_mocks):
        """AC 1: the duration lives in the stylesheet, once, for all of them.

        The mockup repeats `animation-duration:72s` inline on all nine of its
        crossings, and that is the duplication this story was asked to drop.
        It is not cosmetic: a crossing's visible window is a keyframe
        PERCENTAGE of the duration -- 19.5%, which is 14.04s only while the
        duration is 72s -- so every inline copy is another chance for one
        creature's window to quietly stop meaning fourteen seconds.

        Asserted over the MARKUP, because `test_the_cycle_is_written_once`
        already pins the stylesheet half. Between them the number has exactly
        one home. The delay is the opposite case and stays inline: eight
        different values cannot be one rule.

        Scoped to elements wearing `crossing`, which is what the name has
        always meant. A blanket scan for the string over the whole layer said
        the same thing only while every animated element on it was a
        crossing; US-6.3's thirteen droplets each carry their OWN duration as
        data, which is that story's AC 4 rather than a regression of this
        one. The 72s literal is still banned from the markup outright -- no
        element of any world has a reason to write it.

        Counted against `DELAYS` rather than merely proved non-empty, and that
        is what makes the narrowing safe. `STYLED_TAG` reads `class` before
        `style`, so a crossing written with its attributes the other way round
        matches nothing -- and a guard that only asked "did we match at least
        one" would pass on seven of eight while the eighth went unexamined.
        Pinning the count means a crossing the regex cannot see fails here
        instead of slipping through, which is the property the blanket scan
        had for free and a narrowed one has to buy.
        """
        layer = self._layer()
        crossings = [style for classes, style in STYLED_TAG.findall(layer)
                     if CROSSING in classes.split()]

        self.assertEqual(len(crossings), len(DELAYS))
        for style in crossings:
            with self.subTest(style=style):
                self.assertNotIn("animation-duration", style)
        self.assertNotIn(DURATION, layer)

    def test_every_crossing_takes_a_slot_on_the_shared_clock(self, *_mocks):
        """AC 1 and AC 2: who subscribes to the cycle, and where each sits on it.

        The delays ARE the stagger, so they are asserted as the exact
        multiset rather than as "some delays exist". 7s apart with a 14.04s
        window is what holds the stage to two at a time; re-spacing them is
        the change that would quietly make it three, and three reads as
        clutter rather than as a haunting.

        Eight, not seven: the beam rides the saucer's own slot so that it
        fires while the saucer hovers rather than on a clock of its own.

        The pumpkins are deliberately absent from this list. They do not
        cross -- they sit along the bottom for the whole cycle, which is what
        keeps the stage from reading as empty during the ~9.7s the crossings
        leave bare.
        """
        layer = self._layer()

        self.assertEqual(sorted(re.findall(r'animation-delay:(-?\d+s)', layer)), sorted(DELAYS))
        self.assertEqual(len(re.findall(rf'class="[^"]*\b{CROSSING}\b', layer)), len(DELAYS))

    def test_every_element_on_the_stage_wears_the_world_it_belongs_to(self, *_mocks):
        """AC 4: the gate is a class each creature wears, not a list it is on.

        This is the half a selector cannot protect. One rule withdraws
        everything wearing `manor-cast`, so a creature that forgets the class
        is not gated at all -- it would drift through Found Footage and
        through Just the Work, which is the world defined by absence. The
        rule would still be there, still correct, still passing its own test.

        So every direct child of the stage is checked, derived from the
        markup rather than from a list: adding a creature without the class
        fails here on the next run.
        """
        stage = _element(self._layer(), STAGE_ID)

        children = _stage_children(stage)
        self.assertEqual(len(children), sum(CAST.values()))
        for classes in children:
            with self.subTest(element=classes):
                self.assertIn(MANOR_CAST, classes)

    def test_the_mist_takes_its_own_rung_outside_the_stage(self, *_mocks):
        """AC 1: why mist is a sibling of the stage and not a creature on it.

        `#drift` is `position:fixed` with `z-index:0`, so it forms a stacking
        context, and nothing inside it can ever paint above the work at
        `z-index:1`. Mist that drifts BEHIND the portfolio is just a dark
        background; mist in front of it is the difference between a haunted
        room and an unlit one. It therefore takes its own fixed rung on
        US-6.1's ladder, as a child of the container.

        Pinned as containment rather than as a number, the way the rest of
        the ladder is: the rung may be retuned, but moving mist inside the
        stage silently cancels it.
        """
        layer = self._layer()

        self.assertIn(f'id="{MIST_ID}"', layer)
        self.assertNotIn(f'id="{MIST_ID}"', _element(layer, STAGE_ID))

    def test_the_one_that_notices_you_is_governed_by_the_scares_switch(self, *_mocks):
        """The story's Q1, decided: it is a scare, not decoration.

        The approaching ghost is the strongest thing in the Manor set and
        also the closest to a startle, and "theatrical, not frightening"
        (**S11**) cuts both ways on it. Binding it to the scares switch is
        what lets both readings hold: a visitor who leaves scares on gets the
        beat, and one who turned them off keeps the entire theatrical world
        and loses only the lunge.

        It costs NOTHING to do it this way, which is most of the argument.
        US-5.6 built `.scare` as the one container every scare element lives
        inside, so this is ONE CLASS on one element -- no new rule, no new
        selector in that story's block (its contract, line 3), and no script.
        That is the whole assertion here, deliberately: the count of rules
        naming the scares class stays `test_scares.py`'s to make, and the
        cheap way to get this wrong -- a well-meant `.no-scares .ghost` --
        fails there, where that invariant lives.
        """
        page = self.client.get(reverse("ui:home")).content.decode()
        approach = re.search(r'class="ghost approach[^"]*"', _element(page, LAYER_ID)).group()

        self.assertIn(SCARE_HOOK, approach)

    def test_the_two_ghosts_are_one_body_and_one_difference(self, *_mocks):
        """AC 10: one definition, with the single genuine difference as a flag.

        The mockup draws its two ghosts as two separate SVGs, and they are
        NOT identical: the drifting one carries a highlight in each eye and
        the one that notices you has two black voids instead. That absence is
        most of why the second reads as a scare, so it cannot be normalised
        away -- but it is also the ONLY difference in ninety-odd characters
        of otherwise identical path data.

        So the assertion is subtraction, not counting. Strip the highlights
        from the drifting ghost and what is left must be the approaching
        ghost, byte for byte. Counting the highlights instead -- two here,
        none there -- was the first version of this test, and it passed just
        as happily against two separately-maintained copies of the body,
        which is the exact duplication AC 10 forbids and the exact way a path
        fix gets applied to one ghost and not the other.
        """
        layer = self._layer()
        ghosts = re.findall(r'<div class="ghost\b.*?\n\s*</div>', layer, re.S)
        drifting, approach = (re.search(r"<svg.*?</svg>", ghost, re.S).group() for ghost in ghosts)

        self.assertEqual(len(GLINT.findall(drifting)), 2)
        self.assertEqual(GLINT.sub("", drifting), approach)

    def test_the_cast_ships_in_every_world_and_is_withdrawn_by_the_stylesheet(self, *_mocks):
        """AC 4 and **F-18**: the server never knows the world.

        The world is a class the store puts on `<html>` in the browser, and
        the chooser swaps it live with no page load. So withdrawal has to be
        a stylesheet's job -- and the proof that it is, is that a render
        pinned to Just the Work still carries every creature in its bytes.
        """
        pinned = self._layer({THEME_PARAM: CLEAN})

        for creature in CAST:
            with self.subTest(creature=creature):
                self.assertIn(f'class="{creature}', pinned)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ManorCastStylesheetTests(SimpleTestCase):
    """Two tempos per creature, one gate, and no duplicated definition."""

    def _sheet(self):
        """The stylesheet, comments stripped."""
        return _css(self.client.get(reverse("ui:home")).content.decode())

    def test_one_rule_withdraws_the_cast_from_every_other_world(self, *_mocks):
        """AC 4: gated on the CAST, deliberately not on the container.

        `.clean #decor{display:none}` already exists and would have been the
        obvious thing to copy for the other two worlds -- and it would have
        been wrong. The container is shared: US-6.3's band and US-6.4's storm
        are rungs of the same ladder, in worlds that are not Manor. Hiding
        `#decor` to hide Manor's bats would have taken Found Footage's own
        cast down with it, in a story that cannot fail yet.

        `:not()` rather than three world selectors because Arcade's root
        class is the EMPTY STRING -- it IS `:root` -- so there is no class to
        name and a three-world list would leave Manor's ghosts drifting
        through the arcade.
        """
        self.assertIn("display:none", _declaration_block(self._sheet(), WORLD_GATE))

    def test_each_creature_keeps_its_fast_tempo_off_the_slow_clock(self, *_mocks):
        """AC 3: the two tempos, and the one that must not be shared.

        This is the mistake the story warns about in its own voice. The slow
        tempo is the crossing and belongs to the shared 72s cycle; the fast
        one is a wing, a cloak, a candle, a bob, a drift of mist, and belongs
        to the creature. Put a wing-beat on the shared clock and the bat
        flaps once a minute -- which is not a subtle failure, but it is one
        that only appears after watching for a full minute.

        Each fast tempo is asserted with its NUMBER, so a well-meaning tidy
        that folds them into one shared duration fails here.
        """
        css = self._sheet()

        for tempo in TEMPOS:
            with self.subTest(tempo=tempo):
                self.assertIn(tempo, css)

    def test_no_crossing_reaches_for_the_animation_shorthand(self, *_mocks):
        """AC 1: the one way to break the cycle that leaves no trace.

        `animation` is a SHORTHAND, so `animation:haunt linear infinite`
        also declares `animation-duration:0s`. Today that loses to
        `#drift .crossing` on specificity -- (1,1,0) beats (0,1,0) -- so the
        cast would still move and the one-duration contract would merely
        LOOK honoured. The day a later story writes `#drift .ghost{...}` the
        two tie, source order decides, and the whole cast silently stops.

        Nothing else in this module catches that. The shorthand carries no
        `72s` and no `animation-delay`, so `test_the_cycle_is_written_once`
        stays green, the markup is untouched, and the page renders a layer
        of motionless creatures parked at their first keyframe. The comment
        in `base.html` calls this load-bearing; this is what makes that
        claim testable rather than merely stated.

        The creatures are DERIVED from the markup, not listed: whatever wears
        `crossing` is checked, so the next story to put something on the
        shared clock inherits this guard without anybody remembering to
        extend a tuple. Only a creature's OWN rule is
        read -- `.bat .wing` beats at .26s with the shorthand, legitimately,
        because a part is not on the shared clock.
        """
        page = self.client.get(reverse("ui:home")).content.decode()
        css = _css(page)
        names = _crossing_names(_element(page, LAYER_ID))

        self.assertTrue(names, "no crossing found -- the layer or the regex has drifted")
        for name in sorted(names):
            own = [block for selector, block in CSS_RULE.findall(css)
                   if OWN_RULE.match(selector.strip())
                   and re.search(rf"\.{re.escape(name)}\b", selector)]
            with self.subTest(creature=name):
                self.assertTrue(own, f".{name} takes the clock but has no rule of its own")
                self.assertIn("animation-name:", "".join(own))
                self.assertNotIn("animation:", "".join(own))

    def test_the_articulated_parts_rotate_about_their_own_pin(self, *_mocks):
        """AC 3: `transform-origin`, which is load-bearing and silent.

        The mockup pins the bat's wing at the shoulder and the witch's cloak
        at her shoulders, in the SVG's own coordinate space. Ported without
        them the parts still animate -- CSS defaults the origin to the
        element's own box -- so nothing errors, nothing logs, and the wings
        rotate about the corner of the bat. It looks like a bug in the
        artwork rather than a missing declaration, which is exactly why it
        is pinned here by value.
        """
        css = self._sheet()

        for selector, pin in PINS.items():
            with self.subTest(selector=selector):
                self.assertIn(pin, _declaration_block(css, selector))

    def test_no_keyframe_is_defined_twice(self, *_mocks):
        """AC 10: the duplication rule, asked of the whole sheet at once.

        Derived rather than listed. A hand-written list of the names this
        story happens to add can only check itself -- the cheapest way to
        build the next crossing is to copy one of these and rename half of
        it. This fails on the copy, whoever writes it.

        The crossings themselves are NOT duplicates and are not treated as
        any: `haunt` stutters and vanishes, `flit` darts, `fly` arcs,
        `cruise` pauses to hover. Merging them into one shared envelope would
        flatten the ghost's stutter, which is its character. AC 10 forbids a
        definition written twice, not two definitions that differ.
        """
        names = ANY_KEYFRAME.findall(self._sheet())

        self.assertEqual(sorted(names), sorted(set(names)))

    def test_the_artwork_is_sized_by_one_rule_rather_than_six(self, *_mocks):
        """AC 10: the three declarations every creature's SVG shares.

        The mockup writes `display:block; width:100%; height:auto` once per
        creature, six times over, and the only thing that genuinely differs
        between those rules is the filter. One rule on the stage carries the
        shared half.

        Scoped to `#drift`, which keeps the 0x0 `wisp` defs SVG out of it --
        that one is a definition rather than a creature, and it is a sibling
        of the stage precisely so that geometry meant for artwork never
        reaches it. US-6.3's band could not share that rule for the same
        reason: its elements are siblings of the stage too, so they carry a
        second GROUP rule of their own. Two groups, two rules -- what stays
        banned is a rule naming one element, which is the list this test is
        named after.

        Asserted in BOTH directions, the second DERIVED: every rule in the
        sheet that sizes an SVG is collected, and the shared one must be the
        only one there. A per-creature list would have had to be kept in
        step with the cast; this fails on a seventh creature nobody told it
        about. A count
        of `height:auto` across the whole sheet was the first version and
        was both brittle -- any unrelated future use fails it -- and partly
        vacuous, since it passed whether or not the declaration was in the
        rule this test is named after.
        """
        css = self._sheet()
        shared = _declaration_block(css, f"#{STAGE_ID} svg")

        for declaration in ("display:block", "width:100%", "height:auto"):
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, shared)
        sized = [selector.strip() for selector, block in CSS_RULE.findall(css)
                 if "width:100%" in block and selector.strip().endswith("svg")]
        self.assertEqual(sized, [f"#{STAGE_ID} svg", f".{HORROR_CAST} svg"])

    def test_the_phone_widths_drop_the_filters_as_well_as_the_pixels(self, *_mocks):
        """AC 8: what actually costs a weak GPU on this layer.

        Every creature carries a drop-shadow and the ghosts carry a blur, and
        on a weak phone those are the expensive part -- the movement is cheap
        beside them. Shrinking a creature to 60% while it still paints a 26px
        glow saves the cheap half and keeps the dear one, which is the shape
        of optimisation that reads as done and measures as unchanged.

        Declared once, in the 560px block, and on the LAYER so it reaches the
        rungs outside the stage too -- US-6.3's band carries a drop-shadow of
        its own. 400px is narrower, so it inherits this and needs no second
        copy. Read through `_media_block`, which
        matches braces: a slice to the end of the sheet would find this rule
        just as happily if it were moved OUT of the media query, and
        "filters dropped at phone width" and "filters dropped always" are
        very different changes to a page.
        """
        narrow = _media_block(self._sheet(), "(max-width:560px)")

        self.assertIn("filter:none", _declaration_block(narrow, f"#{LAYER_ID} *"))

    def test_the_title_is_lit_by_candlelight_only_in_the_manor(self, *_mocks):
        """AC 1: Manor's atmosphere that is NOT in the decoration layer.

        **S11** promises "candlelight, drifting mist, a glow in the dark".
        The mist is a rung; the candlelight is the page's own title
        guttering, which is where the mockup puts it too.

        A slow shallow gutter rather than the logo's `.flicker`, which is a
        hard two-frame blink borrowed from a failing tube: a title that
        blinks reads as broken, and a title that gutters reads as lit. They
        are separate animations on separate elements for that reason, and
        the assertion checks they stayed separate.

        Manor-gated by its selector, so no other world needs a rule to turn
        it off, and the stillness class stops it with everything else.
        """
        css = self._sheet()
        home = self.client.get(reverse("ui:home")).content.decode()

        self.assertIn('class="display lantern', home)
        self.assertIn("animation:lantern", _declaration_block(css, f".{MANOR} .lantern"))
        self.assertNotIn("lantern", _declaration_block(css, ".flicker"))
