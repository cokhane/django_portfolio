"""Tests for the one strike this site makes, and the four ways to stop it.

A separate module for the reason `test_storm.py` records: `test_decor.py` is
the full one and sits three lines under pylint's `too-many-lines` ceiling, so
each new story in epic 6 takes its own file. The story's Scope names
`tests.py`, which is the API and view suite; the per-story split is the newer
decision and the one the repo follows.

**What this module does NOT re-assert, and the one place that looks like an
exception.** The overlay lives inside `#decor`, and containment is what makes
the layer's existing guarantees cover it for free: `test_decor.py` already
walks the container on all three pages for anything focusable or clickable
(AC 5's focus half), bans `animation-delay` across the whole sheet, and pins
that the container forms no stacking context. `test_effects.py` pins that ONE
rule withdraws the container for REMOVE EFFECTS and that the stylesheet reads
no OS motion preference (AC 9). `test_scares.py` owns the count of the two
`.no-scares` rules AND what they say. `test_found_footage.py` owns the world
gate this story REUSES rather than adds to. `test_chooser.py` owns the bans on
`localStorage` and `console.` in this same script. A second copy of any of
them here would be one more thing to keep in step, so there is none.

The exception is `!important`, which IS checked here even though
`test_decor.py` checks it too. That test filters by SELECTOR TEXT containing
`decor` or `drift`, and none of this story's three selectors contains either
-- the overlay is inside the container in the DOM, not in the stylesheet. So
the rules this story adds are skipped there, and this is first coverage
rather than a second copy. The test says so itself.

**What a Django render cannot see, and why the by-hand pass is the real gate.**
Everything below is markup, script SOURCE and stylesheet text. No test here
runs the timer, because no test here runs a browser: whether the face actually
arrives at 19s, whether the page is genuinely still with scares off, and
whether REMOVE EFFECTS is findable and tappable while a face fills the screen
are all questions for a person. They are the story's five by-hand checks and
they are recorded with their results in its Implementation notes. What is
mechanical is everything that makes those checks possible: the rung, the tree
order that breaks its tie, the gate, the hook, the fold, and the promise that
the way out outranks the face.
"""

import re
from itertools import product
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, HORROR, THEME_PARAM
from .test_chooser import CHOOSER_MARKER, _css, _open_tag
from .test_decor import (
    CEILING,
    HORROR_CAST,
    SCARE_HOOK,
    STAGE_ID,
    WRAPPER_ID,
    _element,
)
from .test_effects import LAYER_ID, _z
from .test_preferences import _inline_script, _render_every_page
from .test_storm import _keyframes
from .test_theme import _colour_literals, _declaration_block, _sections
from .tests import AVAILABILITY, PROJECTS, SKILLS

# The overlay, the shake hook it is paired with, and the class the script puts
# on `<body>` to set both going. Three names, because the split is the design:
# the first two are worn STATICALLY and are inert on their own, and only the
# third -- which exists for 800ms -- turns either into an animation.
LUNGE = "lunge"
SHAKE = "jolt"
STRIKE = "struck"

# The hero, and the only reason the home page is distinguishable from the
# other two renders of `base.html` without a server-side page flag.
HERO_ID = "home"

# US-5.5's cluster. The whole of F-17 is that this number is bigger than the
# rung below, so the way out reads THROUGH the face.
CONTROL_RUNG = 490

# The two numbers the story decided, as the script writes them.
GRACE_MS = 19000
ATTACK_MS = 800

# The attack's length wherever a rule declares it -- `animation:lunge .8s`.
ATTACK = re.compile(r"animation:(?:lunge|jolt) (\.\d+)s")

# A property name at the head of a declaration, for reading a keyframe's set.
PROPERTY = re.compile(r"([a-z-]+):")

# The three a keyframe must never name: each one takes the attack off the
# compositor and repaints the viewport every frame instead.
REPAINTS = ("background", "filter:", "box-shadow")

# `class="in-dark ...` -- the four elements that share rung 455 with the
# overlay, and that it must come after in the markup.
IN_DARK = re.compile(r'class="in-dark ')

# The value of a `class="..."` attribute, read from the start of an opening
# tag's attribute run. A bare `.split()` over the raw text leaves the closing
# quote stuck to the LAST class, so the one that matters most -- the switch
# hook, written last here -- is the one a membership check would miss.
CLASS_ATTR = re.compile(r'class="([^"]*)"')


def _function_body(script, name):
    """The body of `function <name>() {...}` from the tail script.

    The `SET_SCARES` shape in `test_scares.py`, generalised over the name:
    anchored on the closing brace at the function's OWN indentation, which is
    two spaces inside the IIFE. A non-greedy run to the first `}` would stop
    at the first guard clause instead -- and every function this module slices
    is guard-then-act, so that is not a hypothetical.
    """
    opening = f"  function {name}() {{"
    start = script.index(opening) + len(opening)
    return script[start:script.index("\n  }", start)]


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class LungeMarkupTests(SimpleTestCase):
    """What ships, where in the file it ships, and what it refuses to carry."""

    def _home(self, params=None):
        """The home page's HTML, for a world or for the default."""
        return self.client.get(reverse("ui:home"), params or {}).content.decode()

    def test_the_lunge_is_the_last_thing_in_the_layer_and_outside_the_stage(
        self, *_mocks
    ):
        """AC 5 and decision A: tree order is what breaks the tie at 455.

        Three assertions, and the third is the one that is easy to lose. The
        overlay shares its z-index with the four `.in-dark` elements, so the
        CSS cannot decide which paints on top -- document order does, and
        last wins. A later story appending one more rung to this container
        would silently move the face UNDER the eyes it is supposed to arrive
        over, and nothing about the stylesheet would look wrong.

        Outside `#drift` for the reason US-6.3's band records: the stage is a
        stacking context at `z-index:0`, so nothing inside it can paint above
        the work at `1`. A face that renders behind the portfolio is not a
        scare.
        """
        page = self._home()
        layer = _element(page, LAYER_ID)

        self.assertEqual(layer.count(f'class="{LUNGE} '), 1)
        self.assertNotIn(f'class="{LUNGE} ', _element(page, STAGE_ID))
        opening = layer.index(f'class="{LUNGE} ')
        for revealed in IN_DARK.finditer(layer):
            with self.subTest(after=revealed.start()):
                self.assertGreater(opening, revealed.start())
        self.assertNotIn("<div", layer[layer.index(">", opening):])

    def test_the_lunge_wears_the_gate_and_the_hook_and_carries_no_data(self, *_mocks):
        """AC 1, AC 7 and AC 8: two classes do all the governing.

        `horror-cast` is the world gate, REUSED -- so Found Footage alone
        renders it, and Arcade, Manor and Just the Work are answered by one
        rule that already existed. `scare` is US-5.6's switch hook, so the
        switch governs this without a rule of its own.

        It carries no `style=` at all, which makes it the one element on the
        layer that is not data against a shared rule. There is nothing to
        vary: there is exactly one of it and it fills the viewport. WHEN it
        strikes is not markup's business either -- that is a class the script
        puts on `<body>`, so no timing may appear here.
        """
        layer = _element(self._home(), LAYER_ID)
        start = layer.index(f'class="{LUNGE} ')
        opening = layer[start:layer.index(">", start)]

        for worn in (HORROR_CAST, SCARE_HOOK):
            with self.subTest(worn=worn):
                self.assertIn(worn, CLASS_ATTR.match(opening).group(1).split())
        for absent in ("style=", "animation", "tabindex", "role="):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, opening)
        self.assertEqual(_colour_literals(layer), [])

    def test_the_page_wears_the_shake_hook_on_every_page(self, *_mocks):
        """Decision D: the belt can only hit what is already worn.

        `.no-scares .jolt{animation:none !important}` was written by US-5.6
        before there was anything to shake, and it selects a class. A hook
        added by script only at the moment of a strike would not be there for
        that rule to find -- the suppression would be racing the thing it
        suppresses. So `#page` wears it statically, in every world and on
        every page, and is inert because the ANIMATION is declared only under
        `.horror .struck`.

        On all three renders because `base.html` has three renderers and one
        of them is Django's own 404 handler.
        """
        for page, html in _render_every_page(self.client).items():
            with self.subTest(page=page):
                self.assertIn(f'class="{SHAKE}"', _open_tag(html, WRAPPER_ID))

    def test_the_lunge_ships_in_every_world_and_the_stylesheet_withdraws_it(
        self, *_mocks
    ):
        """AC 12 under F-18: the server sends one page, CSS decides what shows.

        This is why AC 12's wording is not followed literally. It asks for a
        test that the markup is ABSENT under Just the Work; absent markup
        would break F-18, which `test_decor.py` pins directly. What the story
        MEANS by it is that nothing renders there, and that is the gate's
        job -- asserted in the stylesheet class below, and twice over by
        `.clean #decor{display:none}`.

        The same reconciliation `test_storm.py` reached for the same reason,
        and it is recorded in both places because a reader meeting either
        test alone would otherwise think the AC had been skipped.
        """
        for world in (HORROR, CLEAN):
            with self.subTest(world=world):
                layer = _element(self._home({THEME_PARAM: world}), LAYER_ID)
                self.assertIn(f'class="{LUNGE} {HORROR_CAST} {SCARE_HOOK}"', layer)

    def test_only_the_home_page_has_a_hero_to_arm_on(self, *_mocks):
        """AC 7: the detail page is exempt, and this is how the script knows.

        The project page is the commercial payload -- a client reading
        `// RESULT` is the single moment the site is doing its job -- so the
        conservative answer the story names is taken and no scare arms there.

        The mechanism is deliberately NOT a server-side "is this home" flag.
        The hero has to exist anyway, because the fold check measures it, so
        asking whether it is present answers the page question for free and
        adds nothing to the template context. The 404 is covered by the same
        fact rather than by a second rule.
        """
        pages = _render_every_page(self.client)

        self.assertIn(f'id="{HERO_ID}"', pages["home"])
        for page in ("detail", "404"):
            with self.subTest(page=page):
                self.assertNotIn(f'id="{HERO_ID}"', pages[page])


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class LungeScriptTests(SimpleTestCase):
    """The half no stylesheet can carry: prevention, rather than hiding."""

    def _script(self):
        """The tail script's source -- the one that owns the controls."""
        return _inline_script(
            self.client.get(reverse("ui:home")).content.decode(), CHOOSER_MARKER
        )

    def test_both_switches_are_asked_before_arming_and_again_before_striking(
        self, *_mocks
    ):
        """US-5.6's contract, lines 1 and 2 -- the reason this story has a test
        module about JavaScript at all.

        A stylesheet cannot stop a timer. `.no-scares .scare{display:none}`
        hides a strike that is already running; it does not prevent the
        sequence, and the story is explicit that a suppressed scare whose
        page-shake still runs is not off. So the question is asked TWICE: once
        before the clock is set, and once more when it goes off, because the
        switch is reachable during the grace period and F-17 says it must be.

        Asserted in both bodies rather than by counting occurrences, so a
        refactor that drops the guard from one of them fails here even if the
        total is unchanged.
        """
        script = self._script()

        for asked in ("window.axePrefs.scares()", "window.axePrefs.effects()"):
            with self.subTest(asked=asked):
                self.assertIn(asked, _function_body(script, "scaresAllowed"))
        for stage in ("arm", "strike"):
            with self.subTest(stage=stage):
                self.assertIn("scaresAllowed()", _function_body(script, stage))

    def test_the_clock_starts_only_when_a_visitor_has_entered_a_world(self, *_mocks):
        """Contract line 5, read literally: the grace period follows ENTRY.

        Two call sites and no more. `closeChooser` is the one place a world is
        entered -- `choose()` is the single write path and a card, the skip
        and Escape all close through it -- so arming there restarts the clock
        on every world change. The other is the else-branch of the final
        guard, which is the visitor who is never asked because they already
        have a world stored.

        The pairing matters: a visitor looking at an open chooser has not
        entered anything yet, and a clock running under the dialog could
        strike the moment they chose. Arming only on the two ways INTO a
        world is what makes that impossible.
        """
        script = self._script()

        self.assertEqual(script.count("arm();"), 2)
        self.assertIn("arm();", _function_body(script, "closeChooser"))
        self.assertIn("openChooser(); } else { arm(); }", script)

    def test_the_grace_and_the_attack_are_the_two_numbers_decided(self, *_mocks):
        """AC 1 and AC 10: the frequency, as the script actually writes it.

        `setTimeout` twice and `setInterval` never -- the whole departure from
        the mockup is that this does not repeat. The mockup runs the lunge on
        an infinite 19s clock, which is the A1 collision the story names: a
        face every 19 seconds will land on a client mid-sentence. One timer
        arms one strike, and a second timer takes the trigger class off again.

        19s is asserted as a named constant rather than as a literal inside
        the call, because the number carries a reason -- one full power-cut
        cycle, so the dark has already rehearsed the visitor and the switch
        has been reachable throughout.
        """
        script = self._script()

        self.assertIn(f"var GRACE_MS = {GRACE_MS};", script)
        self.assertIn(f"var ATTACK_MS = {ATTACK_MS};", script)
        self.assertIn("setTimeout(strike, GRACE_MS)", script)
        self.assertIn("setTimeout(unstrike, ATTACK_MS)", script)
        self.assertNotIn("setInterval", script)

    def test_the_strike_reads_the_fold_and_refuses_to_move_the_visitor(self, *_mocks):
        """AC 6 and AC 10: the A1 guard, and the promise about focus.

        **A1 is the tie-break and the BRD already made it**: legibility beats
        delight. Past half the hero the visitor is reading, so the strike is
        FORGONE rather than deferred -- deferring only moves the ambush
        further into the work, which is the opposite of what the criterion
        asks for.

        The second half is **F-14 and AC 6**. A scare that moves focus takes
        the page away from someone tabbing through it, and the overlay is
        `aria-hidden` inside a container that holds nothing focusable, so
        there is nothing for focus to land on even by accident. The assertion
        is on the sequence's own bodies: nothing here calls `focus`, and
        nothing scrolls the visitor.
        """
        script = self._script()
        striking = _function_body(script, "strike")

        for read in ("window.scrollY", "hero.offsetHeight"):
            with self.subTest(read=read):
                self.assertIn(read, striking)
        for banned in (".focus(", "scrollTo", "scrollIntoView"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, striking)

    def test_which_worlds_scare_is_asked_of_the_stylesheet_and_not_of_a_list(
        self, *_mocks
    ):
        """AC 1's "in the worlds that have one", without a second world list.

        The gap this closes is real and was nearly shipped. The script runs in
        EVERY world, because the gate is CSS-only -- so a visitor who sits in
        Manor for the grace period would spend the one strike invisibly, and
        then never see it after crossing to Found Footage.

        The fix is to ask the page rather than to hold an answer.
        `getClientRects()` is empty when the element or ANY ancestor is
        `display:none`, so one question covers all four gates at once: the
        world gate, the scares switch, REMOVE EFFECTS and Just the Work. A
        list of scaring worlds in JavaScript would have been a SECOND answer
        to a question `ROOT_CLASSES` and the gate rule already answer, and it
        would drift the day a world is added.

        `offsetParent` is asserted absent from the BODY -- not from the whole
        script, which names it in a comment warning against it. It is the
        reflex here and it is WRONG: it is always null for a `position:fixed`
        box, so it would read every world as having no face and no scare
        would ever fire. The comment is worth more than the wider assertion.
        """
        script = self._script()
        asking = _function_body(script, "faceWouldShow")

        self.assertIn("getClientRects().length", asking)
        self.assertNotIn("offsetParent", asking)
        self.assertIn("faceWouldShow()", _function_body(script, "strike"))

    def test_the_sequence_asks_the_os_nothing_and_keeps_its_memory_in_a_variable(
        self, *_mocks
    ):
        """NFR-7 and US-5.5's Q3, both inherited rather than re-implemented.

        Only what this story newly puts at risk is asserted here. That
        `localStorage` and `console.` are absent from this script is already
        owned four times over -- `test_chooser.py` asserts both against this
        very script, and `test_scares.py`, `test_effects.py` and
        `test_preferences.py` each assert them too. A fifth copy would be a
        fifth thing to keep in step.

        What IS new is the other two single-owner rules. The store owns the
        OS motion question and expresses it as a class, so a `matchMedia`
        here would be a second reader of a preference that already has one --
        and it is the obvious thing to reach for when implementing "reduced
        motion means no scare". And `sessionStorage` is named because it is
        the specific key this story decided NOT to add: once per page load
        rather than once per session, so the store stays the only code in
        this repo that touches browser storage. The reasoning is in the
        story's Q1, and this is what would fail if someone reversed it
        without reading that.
        """
        script = self._script()

        for banned in ("sessionStorage", "matchMedia"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, script)
        self.assertIn("document.body.classList.add(STRUCK)", script)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class LungeStylesheetTests(SimpleTestCase):
    """The rung, the tie, the one world that shakes, and the way out."""

    def _sheet(self):
        """The stylesheet, comments stripped."""
        return _css(self.client.get(reverse("ui:home")).content.decode())

    def test_the_lunge_shares_the_top_rung_and_stays_under_the_way_out(self, *_mocks):
        """AC 4 and **F-17**: the escape control reads through the face.

        The acceptance criterion this cannot fully assert is whether a human
        can FIND the control with a face filling the screen -- that is a
        by-hand check and is recorded in the story. What is mechanical is the
        half underneath it: the overlay sits 35 rungs below US-5.5's cluster,
        so the control paints OVER it rather than under, on a phone as well
        as a desktop.

        The rung is asserted EQUAL to `.in-dark` rather than merely `<= 455`,
        because sharing is the decision. US-6.1's Q3 recorded this slot for
        the scare -- "470 in the mockup, 455 here" -- and 455 is already
        shared by four elements, so sharing a rung is this layer's habit
        rather than a new idea. The markup test above owns the tie-break.
        """
        css = self._sheet()

        self.assertEqual(_z(css, f".{LUNGE}"), CEILING)
        self.assertEqual(_z(css, f".{LUNGE}"), _z(css, ".in-dark"))
        self.assertEqual(_z(css, "#site-controls"), CONTROL_RUNG)
        self.assertLess(_z(css, f".{LUNGE}"), CONTROL_RUNG)

    def test_the_overlay_reuses_found_footage_s_gate_and_its_sizing(self, *_mocks):
        """AC 1 and AC 11: this story adds neither a gate rule nor a group rule.

        `test_found_footage.py` pins that exactly ONE rule withdraws that
        world's cast, and the whole value of a marker class is that a new
        element joins the gate by WEARING it rather than by somebody
        remembering a rule. So no selector here may name the overlay and a
        `:not(` together, and the overlay declares no width of its own --
        `.horror-cast svg` sizes it, which is what carries the phone scale
        down with everything else.

        The ordering assertion is a trap this file set for itself.
        `_declaration_block` finds a rule by the literal `.lunge{`, and
        `.struck .lunge{` CONTAINS that text -- written first it would be
        found instead, and the z-index assertion above would silently be
        reading the trigger rule, which has no z-index at all.
        """
        css = self._sheet()

        gating = [part for part in css.split("{") if LUNGE in part and ":not(" in part]
        self.assertEqual(gating, [])
        self.assertNotIn("width", _declaration_block(css, f".{LUNGE} svg"))
        self.assertIn(f".{STRIKE} .{LUNGE}{{", css)
        self.assertLess(css.index(f".{LUNGE}{{"), css.index(f".{STRIKE} .{LUNGE}{{"))

    def test_the_shake_exists_only_in_the_world_that_has_a_face(self, *_mocks):
        """Decision D as code: three worlds are answered by ABSENCE.

        The shake is the one decorative effect in this codebase that is not on
        the decoration layer -- it moves `#page`, which is content -- so every
        guarantee the container hands its rungs is missing and it has to be
        gated on its own. Gating it by PRESENCE, inside Found Footage's block,
        is what makes Manor, Arcade and Just the Work still without a line in
        any of their blocks. The alternative that was rejected --
        `.clean .jolt{animation:none}` -- closes ONE of those three worlds and
        leaves a page that shakes with no face on it in the other two.

        Clean is asserted to contain the word nowhere, because "nothing was
        added to Just the Work" IS the design and a future rule there would
        mean the presence gate had been abandoned.
        """
        css = self._sheet()
        sections = _sections(css)

        self.assertIn(
            "animation:jolt",
            _declaration_block(sections[HORROR], f".{HORROR} .{STRIKE} .{SHAKE}"),
        )
        self.assertNotIn(SHAKE, sections[CLEAN])
        self.assertNotIn(f".{SHAKE}{{animation:{SHAKE}", sections["base"])

    def test_the_attack_is_one_length_wherever_it_is_written(self, *_mocks):
        """The duration appears three times, and a drift would desynchronise it.

        Twice in CSS -- the face and the shake are ONE attack and must start
        and end together, the way US-6.4's two rungs share `13s` -- and once
        in the script, which cannot read a CSS value and must know when to
        take the trigger class off again. Three copies is the cost of there
        being no way for JavaScript to ask a stylesheet how long a rule runs.

        So the test is the single owner of the equality. A shake left running
        after the face has gone is the exact failure this catches, and on a
        page it would read as the site breaking rather than as a scare.
        """
        css = self._sheet()
        lengths = ATTACK.findall(css)

        self.assertEqual(len(lengths), 2)
        self.assertEqual(len(set(lengths)), 1)
        self.assertEqual(float(lengths[0]) * 1000, ATTACK_MS)

    def test_the_strike_moves_nothing_a_phone_has_to_repaint(self, *_mocks):
        """AC 11: a full-viewport scare at 2.8x scale, and still a compositor job.

        `opacity` and `transform` are compositor properties; a background, a
        filter or a shadow inside a keyframe is not, and would repaint the
        whole viewport every frame of the attack. On a phone, where the face
        fills the screen and `#decor *{filter:none}` has already dropped the
        60px halo for exactly this reason, that is the difference between a
        scare and a stutter.

        Asserted over the keyframes rather than the rules, because the rules
        legitimately declare a `filter` -- that is the static half, and the
        phone rule withdraws it.
        """
        css = self._sheet()

        self.assertEqual(
            set(PROPERTY.findall(_keyframes(css, LUNGE))), {"opacity", "transform"}
        )
        self.assertEqual(set(PROPERTY.findall(_keyframes(css, SHAKE))), {"transform"})
        for keyframes, banned in product((LUNGE, SHAKE), REPAINTS):
            with self.subTest(keyframes=keyframes, banned=banned):
                self.assertNotIn(banned, _keyframes(css, keyframes))

    def test_no_rule_this_story_adds_forces_its_way_past_a_preference(self, *_mocks):
        """US-5.6's contract line 3: `!important` is the one thing that would
        defeat the belts, and nothing here writes it.

        The belts are how a visitor's preference is expressed -- a blanket
        `animation:none !important` and a `display:none !important`. A scare
        that matched their weight would tie, and source order would decide
        whether a visitor's choice held. A scare that outranks the switch
        meant to stop it is precisely what BRD §2 calls a defect.

        🚨 **This is NOT the duplicate it looks like.** `test_decor.py`'s
        `test_the_layer_forces_no_motion_property` makes the same check, but
        it filters rules whose SELECTOR TEXT contains `decor` or `drift` --
        and every selector this story adds (`.lunge`, `.struck .lunge`,
        `.horror .struck .jolt`) contains neither, so all three are skipped
        there. The overlay is inside `#decor` in the DOM; its rules are not
        inside it in the stylesheet, and that test reads the stylesheet.

        `animation-delay` is deliberately NOT checked here: `test_decor.py`
        bans it across the WHOLE sheet in one assertion, which is strictly
        stronger than a per-rule copy.
        """
        css = self._sheet()

        for rule in css.split("}"):
            if any(f".{name}" in rule for name in (LUNGE, STRIKE)):
                with self.subTest(rule=rule.strip()[:60]):
                    self.assertNotIn("!important", rule)
