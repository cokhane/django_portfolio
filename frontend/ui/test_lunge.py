"""Tests for the one strike this site makes, and the four ways to stop it.

A separate module for the reason `test_storm.py` records: `test_decor.py` is
the full one and sits three lines under pylint's `too-many-lines` ceiling, so
each new story in epic 6 takes its own file. US-6.5's Scope names
`tests.py`, which is the API and view suite; the per-story split is the newer
decision and the one the repo follows.

**US-6.8 landed here too, and its Scope named somewhere else.** It asks for
`test_scares.py` / `test_effects.py`, and this change touches neither. The
two layers it adds are driven by the SAME `struck` class as the face and
share its rung, its gate and its switch hook -- so every assertion about
them is an assertion about this module's subject, and splitting them across
two files would have put one trigger's guarantees in three places. Those two
modules already own what the Scope wanted from them, and both already cover
the new layers WITHOUT NAMING THEM -- by different mechanisms, which is the
part worth being precise about:

  `test_scares.py`  the HOOK. It pins that suppression is two rules and not
                    a creature list, and the rule is `.no-scares .scare`.
                    The flash and the spray wear `scare`, so they are
                    covered by WEARING it (US-6.8's AC 5).
  `test_effects.py` the CONTAINER. It pins that stillness is exactly three
                    rules, one of them `.no-motion #decor`, which withdraws
                    every rung at once (US-6.8's AC 6 and AC 10).

Neither needed a line added for this story, and adding one to either would
have been the per-element list both tests exist to forbid. Recorded here
because a reader checking that Scope line will otherwise think the AC was
skipped.

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
`decor` or `drift`, and NOT ONE of the selectors these two stories add
contains either -- the `.lunge` family US-6.5 wrote, the `.flash` and
`.gore` families US-6.8 added, the `.struck` trigger rule belonging to each
of those three, and US-6.5's `.horror .struck .jolt`. Their rules are not
inside the container in the stylesheet, so every one is skipped there and
this is first coverage rather than a second copy. The test says so itself.

**The shake is named separately on purpose.** `.horror .struck .jolt` is
the one member that is NOT a decoration: it moves `#page`, the content, so
it is not a child of `#decor` and the "inside the container" reasoning that
covers the other families does not reach it. It is in the set anyway,
because the set is "selectors this module must check for `!important`" and
the filter that admits it is the `.struck` term -- not membership of the
layer. Fold it into a family and the next reader will look for it inside
`#decor` and not find it.

**Deliberately no count here.** The sentence this replaced said "this
story's three selectors" and was wrong twice over by the time anyone
checked: it omitted `.lunge svg`, and US-6.8 then added five more. A number
in this position has to be re-counted by hand on every change to the sheet
and silently rots when it is not, which is the whole failure this module
spends its prose guarding against. The families are what the reader needs;
`test_no_rule_this_story_adds_forces_its_way_past_a_preference` is what
enumerates the actual rules, from the sheet, every time it runs.

**A NOTE ON `AC n` IN THIS FILE, because two stories' criteria now meet in
it.** An unqualified `AC n` is US-6.5's, which is the convention this module
was written under. Every criterion belonging to US-6.8 is written `US-6.8's
AC n` instead -- the numbers collide between the two stories (each one's
`AC 7` is a different promise), so the qualifier is what keeps a citation
readable rather than merely present.

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
from .test_theme import (
    _colour_literals,
    _declaration_block,
    _sections,
    _stylesheet,
)
from .tests import AVAILABILITY, PROJECTS, SKILLS

# The overlay, the shake hook it is paired with, and the class the script puts
# on `<body>` to set both going. Three names, because the split is the design:
# the first two are worn STATICALLY and are inert on their own, and only the
# third -- which exists for 800ms -- turns either into an animation.
LUNGE = "lunge"
SHAKE = "jolt"
STRIKE = "struck"

# US-6.8's two outer thirds of the same impact. They are worn statically and
# are governed by the SAME `struck` class -- one trigger, three layers, which
# is why they are tested here beside the face rather than in a module of their
# own. The ORDER of this tuple is the order they must appear in the markup,
# and that order is the only thing ranking them: all three share rung 455.
FLASH = "flash"
GORE = "gore"
IMPACT = (FLASH, LUNGE, GORE)

# The keyframe set each layer runs. Four animations, ONE attack length.
BLITZ = "blitz"
SPRAY = "spray"
ATTACKERS = (LUNGE, SHAKE, BLITZ, SPRAY)

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
# US-6.8 widened the alternation from two names to four rather than leaving
# its own two unchecked: `animation:blitz` never matched this pattern, so the
# count-of-two assertion below would have passed while the flash and the spray
# drifted freely away from the face they are supposed to land with.
ATTACK = re.compile(rf"animation:(?:{'|'.join(ATTACKERS)}) (\.\d+)s")

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


def _function_body(script, name, indent="  "):
    """The body of `function <name>(...) {...}` from an owned inline script.

    The `SET_SCARES` shape in `test_scares.py`, generalised over the name:
    anchored on the closing brace at the function's OWN indentation, which is
    two spaces inside the IIFE. A non-greedy run to the first `}` would stop
    at the first guard clause instead -- and every function this module slices
    is guard-then-act, so that is not a hypothetical.

    US-6.6 widened it twice rather than writing a third copy beside the two
    this already replaced. The ARGUMENT LIST is now matched rather than
    assumed empty: the side quest slices `onKeydown(event)` and `hits(o)`,
    and a helper that can only find `name()` would have forced a parallel
    regex whose two spellings could then disagree. And `indent` is a
    parameter because that script is nested one level deeper -- it lives
    inside `home.html`'s content block, so its functions sit at four spaces
    rather than two. Both defaults are the old behaviour, so every caller
    above is untouched.
    """
    opening = re.search(rf"^{indent}function {name}\([^)]*\) \{{$", script, re.M)
    assert opening is not None, f"no function {name!r} at this indentation"
    return script[opening.end():script.index(f"\n{indent}}}", opening.end())]


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class LungeMarkupTests(SimpleTestCase):
    """What ships, where in the file it ships, and what it refuses to carry."""

    def _home(self, params=None):
        """The home page's HTML, for a world or for the default."""
        return self.client.get(reverse("ui:home"), params or {}).content.decode()

    def test_the_impact_is_three_layers_in_one_order_outside_the_stage(
        self, *_mocks
    ):
        """US-6.5's AC 5 and US-6.8's AC 2 -- tree order breaks the tie at 455.

        All three layers share their z-index with each other AND with the
        four `.in-dark` elements, so the CSS cannot decide which paints on
        top -- document order does, and later wins. That makes the SEQUENCE
        the design: the flash is the glare the face arrives out of, so it
        goes behind; the spray is what the strike leaves on the lens, so it
        goes over. Written in any other order the stylesheet still looks
        entirely correct and the scare is wrong.

        🚨 US-6.5 ASSERTED THAT THE FACE WAS LAST, AND US-6.8 MADE THAT
        FALSE. This test was rewritten rather than relaxed: what replaced
        the old `assertNotIn("<div", ...)` is the same guarantee moved to
        the element that now holds it -- the SPRAY is last, so appending a
        rung still cannot slip under the blood unnoticed.

        Outside `#drift` for the reason US-6.3's band records: the stage is a
        stacking context at `z-index:0`, so nothing inside it can paint above
        the work at `1`. A face that renders behind the portfolio is not a
        scare.
        """
        page = self._home()
        layer = _element(page, LAYER_ID)
        stage = _element(page, STAGE_ID)
        at = {}

        for layer_name in IMPACT:
            with self.subTest(layer=layer_name):
                self.assertEqual(layer.count(f'class="{layer_name} '), 1)
                self.assertNotIn(f'class="{layer_name} ', stage)
            at[layer_name] = layer.index(f'class="{layer_name} ')
        self.assertEqual(sorted(at, key=at.get), list(IMPACT))
        for revealed in IN_DARK.finditer(layer):
            with self.subTest(after=revealed.start()):
                self.assertGreater(at[FLASH], revealed.start())
        self.assertNotIn("<div", layer[layer.index(">", at[GORE]):])

    def test_each_layer_wears_the_gate_and_the_hook_and_carries_no_data(
        self, *_mocks
    ):
        """US-6.8's AC 1 and AC 5. AC 6 and AC 7 are NOT this method's.

        `horror-cast` is the world gate, REUSED -- so Found Footage alone
        renders it, and Arcade, Manor and Just the Work are answered by one
        rule that already existed. `scare` is US-5.6's switch hook, so the
        switch governs this without a rule of its own.

        **ALL THREE wear the SAME pair, and that is US-6.8's AC 5 in the
        markup.** A flash that wore the gate but not the hook would still
        fire with scares off -- a white blast with no face behind it, which
        is a worse experience than the scare it was meant to replace. The
        switch reaching all three is a property of what they WEAR, so it is
        asserted here on every one of them rather than once on the face.

        🚨 **US-6.8's AC 6 IS NOT ASSERTED HERE, because wearing these does
        not buy it.** No `.no-motion` rule keys on `scare` or `horror-cast`
        at all. REMOVE EFFECTS is the stillness block -- the three rules
        `test_effects.py` pins: a universal `animation:none`, one rule
        carrying both `body::before` and `body::after`, and
        `.no-motion #decor`. Not one of them looks at what an element
        wears. That guarantee belongs to `test_effects.py`, which owns the
        whole block, and this method would pass unchanged if every rule in
        it were deleted. Citing US-6.8's AC 6 here would point the next
        reader at the wrong mechanism -- and writing it BARE would point
        them at US-6.5's AC 6, the promise about focus, which belongs to
        another test in this file entirely.

        🚨 **US-6.8's AC 7 IS NOT THIS METHOD'S EITHER, and the reason is
        worth spelling out because the obvious reading is wrong.** Its three
        promises have three different owners, and none of them is the pair
        asserted below:

          takes no CLICK     `#decor{pointer-events:none}`, inherited
          is not ANNOUNCED   `aria-hidden` on `#decor`, over its subtree
          takes no FOCUS     NEITHER of those. `aria-hidden` does not
                             remove anything from the tab order, and
                             `pointer-events` has nothing to do with
                             focus -- `test_keyboard.py` says so in those
                             words. It is per-element: a plain `<div>`
                             with no `tabindex`, and `focusable="false"`
                             on every `<svg>`, which `test_keyboard.py`
                             and `test_decor.py` pin across the whole
                             container on all three pages.

        So the container buys two of the three and the markup buys the
        third, and `base.html`'s own ladder row is labelled "NO CLICK, NO
        SCREEN READER" for exactly that reason -- it leaves focus out on
        purpose. Nothing below asserts any of the three.

        What IS below is this method's own subject: none of the three
        carries a `style=` or a timing, which makes them the elements on
        the layer that are not data against a shared rule. There is nothing
        to vary -- there is exactly one of each and each fills the viewport
        -- and WHEN they strike is a class the script puts on `<body>`, so
        no timing may appear here either.
        """
        layer = _element(self._home(), LAYER_ID)

        for layer_name in IMPACT:
            start = layer.index(f'class="{layer_name} ')
            opening = layer[start:layer.index(">", start)]
            for worn in (HORROR_CAST, SCARE_HOOK):
                with self.subTest(layer=layer_name, worn=worn):
                    self.assertIn(worn, CLASS_ATTR.match(opening).group(1).split())
            for absent in ("style=", "animation"):
                with self.subTest(layer=layer_name, absent=absent):
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

        US-6.8's AC 9 asks the same of its two layers in the same words, so
        it is answered the same way and in the same loop.
        """
        for world, layer_name in product((HORROR, CLEAN), IMPACT):
            with self.subTest(world=world, layer=layer_name):
                layer = _element(self._home({THEME_PARAM: world}), LAYER_ID)
                self.assertIn(
                    f'class="{layer_name} {HORROR_CAST} {SCARE_HOOK}"', layer
                )

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

        **US-6.8's AC 2: all THREE layers take one number, which is what makes
        the markup's order load-bearing.** The mockup ranks them 468 / 470 /
        472 and not one of those survives the ceiling. Asserting equality
        across the three is what stops the next reader "fixing" the stacking
        with a number -- the moment one of them differs, tree order stops
        being the mechanism and the markup test above starts guarding
        nothing.
        """
        css = self._sheet()

        for layer_name in IMPACT:
            with self.subTest(layer=layer_name):
                self.assertEqual(_z(css, f".{layer_name}"), CEILING)
                self.assertEqual(_z(css, f".{layer_name}"), _z(css, ".in-dark"))
                self.assertLess(_z(css, f".{layer_name}"), CONTROL_RUNG)
        self.assertEqual(_z(css, "#site-controls"), CONTROL_RUNG)

    def test_the_overlay_reuses_found_footage_s_gate_and_its_sizing(self, *_mocks):
        """AC 1 and AC 11: this story adds neither a gate rule nor a group rule.

        `test_found_footage.py` pins that exactly ONE rule withdraws that
        world's cast, and the whole value of a marker class is that a new
        element joins the gate by WEARING it rather than by somebody
        remembering a rule. So no selector here may name one of the three
        and a `:not(` together, and neither overlay declares a width of its
        own -- `.horror-cast svg` sizes them, which is what carries the
        phone scale down with everything else.

        **The gate half is asserted for all THREE layers, not just the
        face.** US-6.8 added two more elements to this world, and a gate
        rule written for either of them would be exactly the per-element
        list this test exists to forbid -- checking only the face would
        leave two thirds of the scare unguarded.

        The ordering half of this test MOVED OUT rather than growing: it is
        the same trap for all three layers now, so it belongs to
        `test_each_base_rule_is_written_before_the_trigger_that_contains_it`
        below, which owns it for `.flash`, `.lunge` and `.gore` together.
        Asserting it here too would give one guarantee two owners, and this
        file's own rule (see the attack-length test) is that there is
        exactly one owner of an equality.
        """
        css = self._sheet()

        for layer_name in IMPACT:
            with self.subTest(layer=layer_name):
                gating = [part for part in css.split("{")
                          if layer_name in part and ":not(" in part]
                self.assertEqual(gating, [])
        for sized in (LUNGE, GORE):
            with self.subTest(layer=sized):
                self.assertNotIn("width", _declaration_block(css, f".{sized} svg"))

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
        """The duration appears five times, and a drift would desynchronise it.

        Four times in CSS -- the flash, the face, the spray and the shake
        are ONE attack and must start and end together, the way US-6.4's two
        rungs share `13s` -- and once in the script, which cannot read a CSS
        value and must know when to take the trigger class off again. Five
        copies is the cost of there being no way for JavaScript to ask a
        stylesheet how long a rule runs.

        So the test is the single owner of the equality. A shake left running
        after the face has gone is the exact failure this catches, and on a
        page it would read as the site breaking rather than as a scare.

        🚨 THE SCRIPT'S COPY IS A CEILING ON THE OTHER FOUR, not merely a
        twin of them, and that is why US-6.8's spray is `.8s` and not the
        mockup's 3.534s. `unstrike` removes `struck` at `ATTACK_MS`, which
        CANCELS any rule still running -- a longer animation would not play
        on past the face, it would vanish in one frame. The story's unknown
        1 was decided on exactly this: a lingering stain is a change to the
        trigger, not to a keyframe, and the trigger is out of its scope.
        """
        css = self._sheet()
        lengths = ATTACK.findall(css)

        self.assertEqual(len(lengths), len(ATTACKERS))
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

        🚨 THE FLASH IS THE ONE THIS MATTERS MOST FOR, and it is the one
        most likely to be broken by a well-meaning edit. Its whole effect IS
        a background -- a full-viewport radial gradient -- so animating that
        background is the obvious way to write it and would repaint every
        pixel on the screen every frame. It is declared ONCE in the static
        rule and only `opacity` moves, which is the difference between a
        scare and a stutter on a phone.
        """
        css = self._sheet()
        moves = {LUNGE: {"opacity", "transform"}, SHAKE: {"transform"},
                 BLITZ: {"opacity"}, SPRAY: {"opacity", "transform"}}

        for keyframes, expected in moves.items():
            with self.subTest(keyframes=keyframes):
                self.assertEqual(
                    set(PROPERTY.findall(_keyframes(css, keyframes))), expected
                )
        for keyframes, banned in product(ATTACKERS, REPAINTS):
            with self.subTest(keyframes=keyframes, banned=banned):
                self.assertNotIn(banned, _keyframes(css, keyframes))

    def test_each_base_rule_is_written_before_the_trigger_that_contains_it(
        self, *_mocks
    ):
        """The selector-order trap US-6.5 recorded, now pinned for all three.

        `_declaration_block` anchors on `selector{` and takes the FIRST
        occurrence. `.struck .flash{` contains the literal `.flash{`, so a
        trigger rule written above its base rule is what every lookup finds
        -- and the rung assertion above would then read a rule that declares
        no `z-index` at all and fail with a message about the wrong thing.

        US-6.5 hit this with `.lunge` and left both a comment and an
        assertion of its own, which lived in
        `test_the_overlay_reuses_found_footage_s_gate_and_its_sizing`.
        US-6.8 inherited the same trap twice over, so that assertion was
        MOVED here and generalised rather than copied -- three layers with
        one trap between them want one owner, and leaving the original in
        place would have meant a future change to this convention failing
        in two tests and being half-fixed in one.
        """
        css = self._sheet()

        for layer_name in IMPACT:
            with self.subTest(layer=layer_name):
                self.assertLess(
                    css.index(f".{layer_name}{{"),
                    css.index(f".{STRIKE} .{layer_name}{{"),
                )

    def test_the_spray_is_stretched_to_the_viewport_and_not_sized_by_a_query(
        self, *_mocks
    ):
        """US-6.8's AC 11: one drawing covers 320px and a desktop, no query.

        `.horror-cast svg{display:block; width:100%}` already exists and is
        REUSED, so the only declaration this story owes is the height -- the
        wrapper is `inset:0` and `width:100%` alone would leave the artwork
        at its intrinsic aspect ratio partway down the screen.

        **The absence of a `width` here is NOT asserted in this method**,
        although it is the natural other half of the sentence above.
        `test_the_overlay_reuses_found_footage_s_gate_and_its_sizing` makes
        that check for `.lunge` and `.gore` together, which is the right
        home for it: the claim is "neither layer re-declares what the group
        rule already gives", and that is one guarantee about two elements
        rather than a fact about the spray. Asserting it here as well would
        give it two owners -- the same duplication that method's own
        docstring records giving up the ordering assertion to avoid.

        The other half of that AC is `preserveAspectRatio="none"` in the
        partial, which is what makes the stretch a stretch rather than a
        crop. Asserted on the markup because that is where it lives.
        """
        own = _declaration_block(self._sheet(), f".{GORE} svg")
        artwork = _element(self.client.get(reverse("ui:home")).content.decode(),
                           LAYER_ID)

        self.assertIn("height:100%", own)
        self.assertIn('preserveAspectRatio="none"', artwork)

    def test_the_flash_records_the_photosensitivity_margin_it_spends(
        self, *_mocks
    ):
        """US-6.8's AC 4: the flash's margin, written down and pinned.

        🚨 THIS TEST ASSERTS A COMMENT, WHICH IS UNUSUAL AND DELIBERATE. The
        margin is one flash: WCAG 2.3.1 fails content flashing MORE THAN
        THREE times in any one-second period over a large area, `blitz` has
        exactly two bright peaks, and the whole animation is `.8s` so both
        fall inside one second. Nothing about the keyframes SAYS that. A
        later story tightening the timing or adding a third peak would be
        making a safety decision while believing it was making a taste one,
        and the only thing that can stop it is prose sitting beside the
        numbers.

        So the prose is load-bearing here in a way it is not elsewhere in
        this sheet, and that is what earns it an assertion. Read from the
        RAW stylesheet, because `_css` strips exactly what this is checking.

        The peak count is asserted too, from the keyframes themselves, so
        the comment cannot drift away from the thing it describes: if a
        third peak is ever added, this fails even if the prose is updated to
        match it.
        """
        page = self.client.get(reverse("ui:home")).content.decode()
        raw = _stylesheet(page).lower()
        peaks = [float(f".{found}") for found in
                 re.findall(r"opacity:\.(\d+)", _keyframes(_css(page), BLITZ))]

        self.assertEqual(len([peak for peak in peaks if peak > 0.5]), 2)
        for recorded in ("2.3.1", "three times", "one-second", "0.772"):
            with self.subTest(records=recorded):
                self.assertIn(recorded, raw)

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
        and NOT ONE selector either story adds contains either, so every one
        of them is skipped there. The layers are inside `#decor` in the DOM;
        their rules are not inside it in the stylesheet, and that test reads
        the stylesheet. So this is first coverage, not a second copy.

        **The set is named by FAMILY and never by count**, for the reason
        the module docstring gives: the `.lunge` family US-6.5 wrote, the
        `.flash` and `.gore` families US-6.8 added, the `.struck` trigger
        rule belonging to each of those three, and US-6.5's
        `.horror .struck .jolt`, which the `STRIKE` term admits even though
        it belongs to no layer -- it moves `#page`, not the decoration.
        The loop below is what enumerates them: `IMPACT` is what admits a
        new LAYER and `STRIKE` is what admits a new trigger rule, so there
        is no list here to fall out of step with the sheet.

        `animation-delay` is deliberately NOT checked here: `test_decor.py`
        bans it across the WHOLE sheet in one assertion, which is strictly
        stronger than a per-rule copy.
        """
        css = self._sheet()

        for rule in css.split("}"):
            if any(f".{name}" in rule for name in (*IMPACT, STRIKE)):
                with self.subTest(rule=rule.strip()[:60]):
                    self.assertNotIn("!important", rule)
