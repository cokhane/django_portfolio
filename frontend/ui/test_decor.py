"""Tests for the stage epic 6's decoration is built on, and its 72-second clock.

A separate module for the reason `test_theme.py`, `test_hire_me_panel.py`,
`test_preferences.py`, `test_chooser.py`, `test_effects.py` and
`test_scares.py` each record: `tests.py` is already near pylint's
`too-many-lines` ceiling. The story's Scope names `tests.py` because it was
written before that split; the split is the newer decision and the one the
repo follows.

**This story ships the stage, not the cast.** No creature is in scope, so
nothing here asserts that anything moves. What a render genuinely carries is
the structure 6.2 to 6.5 inherit, and that is what is pinned:

1. **The container cannot take a click or a focus** (**NFR-8**, **F-14**) --
   the fence, asserted while the layer is empty precisely so the first
   creature is built inside it.
2. **The container is NOT a stacking context**, which is the one property the
   whole ladder rests on and the one nothing on screen would show.
3. **The cycle is written once** -- one duration, in one rule (**AC 11**).
4. **Both switches withdraw the layer whole**, and the world defined by
   absence never renders it (**S11**).

What a Django render cannot carry is anything about motion: it renders
templates, it does not run them. **AC 4** -- never more than two of nine on
screen across a full 72-second cycle -- was measured against the mockup's own
nine delays and envelopes, and the counts are recorded in the story's
Implementation notes. The same is true of **AC 10**'s visual half at 320px.
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, THEME_PARAM
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

        Trivially true today -- the stage is empty. That is the point. The
        assertion exists so that the first creature 6.2 writes is built inside
        a boundary that is already enforced, rather than against one somebody
        has to remember. A decorative shape that swallows a tap is a dead
        patch over work a visitor is reaching for, and on a phone it is a tap
        that simply does nothing.

        `pointer-events` is asserted absent from the markup as well as set on
        the container in CSS: the container's rule cannot protect the page
        from a child that re-enables pointers on itself.
        """
        layer = _element(self._page(), LAYER_ID)

        for focusable in ("<a", "<button", "tabindex", "pointer-events"):
            with self.subTest(focusable=focusable):
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
        560px and six more at 400px. One token the stage redefines does the
        same job, and a creature that arrives later is scaled without anyone
        editing a media block.

        `rindex` because the chooser owns a `560px` block of its own, earlier
        in the stylesheet; the layer's is the last. Size is read as
        `var(--decor-scale,1)` and the token is declared nowhere else, so the
        fallback IS the full-size default and there is no second copy to
        drift from this one.
        """
        css = self._sheet()

        for width, scale in SCALES:
            with self.subTest(width=width):
                block = css[css.rindex(f"@media (max-width:{width})"):]
                self.assertIn(scale, _declaration_block(block, f"#{STAGE_ID}"))
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
