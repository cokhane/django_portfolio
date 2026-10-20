"""Tests for the switch that turns the scares off and leaves the world on.

A separate module for the reason `test_theme.py`, `test_hire_me_panel.py`,
`test_preferences.py`, `test_chooser.py` and `test_effects.py` each record:
`tests.py` is already near pylint's `too-many-lines` ceiling. The story's Scope
names `tests.py` because it was written before that split; the split is the
newer decision and the one the repo follows.

**Django renders templates; it does not run them.** So nothing here proves the
switch WORKS -- not that pressing it suppresses a scare, not that the state
survives a reload, and above all not AC 2, the four effects/scares
combinations. Those were run against the rendered store under a fake DOM, the
way US-5.5 proved its own truth table, and the result is recorded in the
story's Status. What a render genuinely carries is pinned here instead:

1. **The switch is absent, not dead, without JavaScript** -- it ships inside
   the cluster the server renders `hidden` (**A1**).
2. **The server never ships the scare class**, because it cannot read a
   preference that lives in the browser.
3. **The two preferences are not collapsed into one.** This is the property
   the story is most explicit about and the one nothing on screen would show:
   REMOVE EFFECTS implying scares-off would look correct in every manual
   check and would silently restore a scare on the day effects came back.
4. **The switch is absent in the world with no scare**, rather than present
   and inert (**AC 6**).

AC 9's mechanical half -- the cluster wraps and every button clears 44px --
is NOT re-asserted here. `test_effects.py::test_the_cluster_wraps_at_phone_width`
already pins it and says in its own docstring that it does so *because* this
story adds a third button. What is new here is that the third button carries
the class that inherits the floor, which is asserted on the tag below.
"""

import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .context_processors import CLEAN, THEME_PARAM
from .test_chooser import CHOOSER_MARKER, _css, _open_tag
from .test_effects import CONTROL_ID as STILLNESS_ID
from .test_preferences import (
    _assert_work_survives_without_scripts,
    _inline_script,
    _owned_script,
    _render_every_page,
    _without_scripts,
)
from .test_theme import _declaration_block, _root_tag, _rules_naming, _world_join
from .tests import AVAILABILITY, PROJECTS, SKILLS

SWITCH_ID = "toggle-scares"
SCARE_CLASS = "no-scares"

# The mockup's two strings, which F-18 freezes: a world changes the palette,
# never the words.
LABELS = ("SCARES: ON", "SCARES: OFF")

# `setScares`'s body, anchored on the closing brace at the function's OWN
# indentation rather than on the first `}` after it. The difference is not
# hypothetical: a slice ending at the first brace would silently shorten the
# day anyone added a conditional inside, and the assertions below -- which are
# all `assertNotIn` -- would then pass against the shorter text without
# testing anything. A guard that cannot fail is worse than no guard.
SET_SCARES = re.compile(r"function setScares\(on\) \{(.*?)\n  \}", re.S)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ScaresSwitchMarkupTests(SimpleTestCase):
    """What the server actually sends, on every page a visitor can reach."""

    def _home(self, query=None):
        """The home page's HTML, optionally pinned to a world."""
        return self.client.get(reverse("ui:home"), query or {}).content.decode()

    def test_the_switch_ships_inside_the_hidden_cluster_on_every_page(self, *_mocks):
        """AC 1 and AC 8, and the ordering that puts the two preferences together.

        Three things at once, because they are one property. The switch is on
        the page; it is INSIDE `#site-controls` and AFTER the stillness
        control, so the two preference switches are adjacent in Tab order
        rather than separated by the way back into the chooser; and the
        cluster carries `hidden` in the bytes the server sends. Take the last
        away and a visitor with JavaScript off meets a switch that cannot do
        the one thing it names.

        Asserted per page because `base.html` has three renderers and one of
        them is not ours -- Django's own `page_not_found`. A mechanism wired
        into a view would be absent exactly there, on the page a visitor
        reaches by mistake and most wants a way out of.
        """
        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                cluster = html[html.index('id="site-controls"'):html.index('id="open-chooser"')]
                self.assertIn(f'id="{SWITCH_ID}"', cluster)
                self.assertLess(cluster.index(f'id="{STILLNESS_ID}"'), cluster.index(SWITCH_ID))
                self.assertIn(" hidden>", _open_tag(html, "site-controls"))

    def test_the_switch_is_a_labelled_toggle_that_inherits_the_tap_target(self, *_mocks):
        """AC 5, AC 7 and the half of AC 9 that is this story's to carry.

        `aria-pressed` is what makes it a toggle rather than a thing that
        happens. Its polarity is the OPPOSITE of the stillness control's, and
        deliberately: this label names the THING ("SCARES: ON"), so pressed
        means the scares are on, while "REMOVE EFFECTS" names an ACTION, so
        pressed there means the action is applied. Each agrees with the words
        beside it, which is what a screen reader reads out.

        No `aria-label`, and that is asserted rather than merely omitted. The
        stillness control needs one because "REMOVE EFFECTS" does not say what
        it removes them from; "SCARES: ON" already states the state, and a
        second F-18-frozen string would buy no reader anything while giving
        the next editor two places to keep in agreement.

        `class="btn"` is the new half of AC 9. `test_effects.py` pins the 44px
        floor on `#site-controls .btn`, so a third button written without that
        class would clear every assertion in this suite and still ship a 34px
        tap target on a phone.

        A `<button>` rather than a styled `<div>` is the whole of AC 7: it is
        keyboard-reachable and Space/Enter-operable by construction.
        """
        tag = _open_tag(self._home(), SWITCH_ID)

        self.assertIn('type="button"', tag)
        self.assertIn('class="btn"', tag)
        self.assertIn('aria-pressed="true"', tag)
        self.assertNotIn("aria-label=", tag)
        self.assertIn(f">{LABELS[0]}</button>", self._home())

    def test_the_server_never_ships_the_class(self, *_mocks):
        """AC 1: the preference lives in the browser, so the server does not guess.

        The class arrives from the store, on the client. If the server ever
        put it on `<html>` it would be guessing for every visitor at once --
        and a visitor who never turned the scares off would have them
        suppressed until their own script corrected it.

        Checked on a pinned render too, because `?theme=` is the one thing
        that CAN change the root tag and is therefore the one place a scare
        class could plausibly be smuggled in.
        """
        for query in (None, {THEME_PARAM: CLEAN}, {THEME_PARAM: "horror"}):
            with self.subTest(query=query):
                self.assertNotIn(SCARE_CLASS, _root_tag(self._home(query)))

    def test_the_page_reads_without_the_switch(self, *_mocks):
        """AC 8 and AC 11: the work survives the visitor who cannot run it.

        This story adds a third fixed, always-on-screen element to every
        page, which is exactly the kind of addition that quietly takes a site
        away from someone who cannot dismiss it.

        The cluster's `hidden` attribute is NOT re-asserted here -- the test
        above pins it on all three pages, and it is static markup, so
        stripping the scripts cannot change it. What is unique to this test is
        the half that could change: the work still being on the page.
        """
        _assert_work_survives_without_scripts(self, _without_scripts(self._home()))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ScaresScriptTests(SimpleTestCase):
    """Which script owns what -- the half a template render can see."""

    def _home(self):
        """The home page's HTML."""
        return self.client.get(reverse("ui:home")).content.decode()

    def test_the_store_applies_the_class_before_paint(self, *_mocks):
        """AC 1: one apply path, and it runs in `<head>`.

        US-5.3 shipped `setScares` PERSISTING ONLY, because the class it would
        have applied had no stylesheet behind it. This story defines that
        class, so the apply moved into the store rather than into the switch
        -- keeping exactly one place that decides what the root element wears,
        the same property `test_chooser.py` pins for the world and
        `test_effects.py` for stillness.

        The call sits ABOVE the pinned-render guard because `?theme=` pins the
        world and nothing else: a tester looking at one world keeps their own
        preference. Below that guard, every `?theme=` render would silently
        ignore it.
        """
        owned = _owned_script(self._home())

        self.assertIn(SCARE_CLASS, owned)
        self.assertLess(owned.index("applyScares(scares())"), owned.index("if (pinned)"))
        self.assertNotIn(SCARE_CLASS, _inline_script(self._home(), CHOOSER_MARKER))

    def test_the_switch_writes_only_through_the_store(self, *_mocks):
        """AC 1: the switch is a view, and the store owns NFR-7's guards.

        US-5.3 put every `localStorage` access behind a `try` in one script and
        `test_preferences.py` counts them -- exactly two. A switch reaching
        storage directly would be a third, free to get a private window wrong,
        and that count would stop meaning what it says.
        """
        script = _inline_script(self._home(), CHOOSER_MARKER)

        self.assertIn("window.axePrefs.setScares(", script)
        self.assertNotIn("localStorage", script)
        self.assertNotIn("console.", script)

    def test_the_two_preferences_are_never_collapsed(self, *_mocks):
        """AC 2, as far as a render can carry it -- and it is the story's point.

        Stillness means no scare in practice, so making REMOVE EFFECTS imply
        scares-off is the tempting simplification. It is also the one the
        story forbids, because the two preferences must survive each other:
        turn effects off, turn scares off, turn effects back on, and the scare
        must STAY off.

        A template render cannot press three buttons, so what is pinned here
        is the structural precondition for that sequence -- two distinct
        storage keys, and neither setter reaching into the other's class. The
        sequence itself was run against this store under a fake DOM and is
        recorded in the story's Status.

        The assertion is deliberately about `setScares`'s BODY rather than the
        whole script: the file legitimately mentions both preferences all over,
        and a test that forbade the word would fail on the comments explaining
        why they are separate.
        """
        owned = _owned_script(self._home())
        found = SET_SCARES.search(owned)

        self.assertIsNotNone(found, "setScares is no longer a function this can slice")
        body = found.group(1)
        self.assertIn("KEY.scares", owned)
        self.assertIn("KEY.effects", owned)
        self.assertIn("applyScares(on)", body)
        self.assertNotIn("Effects", body)
        self.assertNotIn("no-motion", body)

    def test_the_label_is_corrected_before_the_cluster_is_revealed(self, *_mocks):
        """AC 5: the no-flash ordering, which nothing else would catch.

        The server renders the scares-on wording because it has no preference
        to read. For a visitor who turned them off that wording is wrong, and
        the script fixes it -- but only if it fixes it while the cluster is
        still `hidden`. The other way round, every page load shows SCARES: ON
        flipping to SCARES: OFF after the paint.

        `rindex`, and the count beside it, are not fussiness -- the same
        assertion written with `index` in `test_effects.py` could not fail.
        The call is made TWICE: once by the click listener, which sits earlier
        in the script than the reveal, so the earliest occurrence precedes
        `controls.hidden` however the reveal is ordered. The count is what then
        stops the whole assertion being satisfied by the listener alone if the
        reveal-time call is deleted outright.
        """
        script = _inline_script(self._home(), CHOOSER_MARKER)

        self.assertEqual(script.count("renderScares();"), 2)
        self.assertLess(
            script.rindex("renderScares();"), script.index("controls.hidden = false")
        )


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ScaresStylesheetTests(SimpleTestCase):
    """One class, one block, and the world that has nothing to govern."""

    def _home(self, query=None):
        """The home page's HTML, optionally pinned to a world."""
        return self.client.get(reverse("ui:home"), query or {}).content.decode()

    def test_suppression_is_two_hooks_and_not_a_creature_list(self, *_mocks):
        """AC 10: the property that keeps this story from rotting.

        Two rules. Not the mockup's six, and not six-plus-one-per-creature as
        epic 6 lands: a per-creature opt-out list is a list somebody has to
        remember to add to, and the whole reason this story ships BEFORE the
        things it withdraws is that nobody will. `.scare` is the one container
        every scare element goes in; `.jolt` is the one case that cannot live
        inside it, because it shakes content that stays on the page.

        `_world_join` is the other half, and it guards a mistake that is
        silent rather than ugly: `test_theme.py` finds a world's palette by its
        class name followed by an opening brace, so a rule joining this class
        to a world's would be found first and read as that world's palette --
        for every token the suite checks.
        """
        css = _css(self._home())

        self.assertEqual(len(_rules_naming(css, SCARE_CLASS)), 2)
        self.assertIsNone(
            _world_join(css, SCARE_CLASS), "a world class is joined to the scare class"
        )

    def test_suppression_stops_the_work_rather_than_covering_it(self, *_mocks):
        """AC 4, the half a stylesheet can carry.

        `display:none` cancels a running animation rather than painting over
        it, so withdrawing the container genuinely stops its work on a weak
        device. The shake needs `animation:none` instead, because the element
        it moves is content that has to stay on the page.

        `animation:none` on the shake is NOT redundant beside the stillness
        class, and that is the whole of S14: scares off with effects ON is the
        combination the two switches exist to make possible, and in it the
        blanket motion rule is not applied.

        The half this cannot assert -- that epic 6's sequence never STARTS --
        is a JavaScript contract, recorded in the story's Implementation notes
        and in the stylesheet comment above these two rules.
        """
        css = _css(self._home())

        self.assertIn("display:none", _declaration_block(css, f".{SCARE_CLASS} .scare"))
        self.assertIn("animation:none", _declaration_block(css, f".{SCARE_CLASS} .jolt"))

    def test_the_switch_is_absent_where_there_is_nothing_to_govern(self, *_mocks):
        """AC 6: Just the Work has no scare, so it does not offer the switch.

        S11 defines that world by absence -- "No blood, no creatures, nothing
        that moves" -- so a switch there would flip a label and change nothing
        else, which is exactly the dead control the story forbids. It is
        `display:none` rather than a lighter touch because that drops the
        button from Tab order and from the screen reader's tree too: absent,
        not merely invisible.

        Expressed in CSS rather than in script because a world swaps LIVE
        through the chooser, with no page load. A rule re-reads on the same
        frame the root class changes; a script would need a hook into the
        choosing path and a second list of which worlds scare -- a list that
        is still US-6.5's open question.

        The second assertion is F-18 and is the reason this is a stylesheet
        rule at all: the MARKUP is identical in every world. A world withdraws
        the control from view; it does not change what the document says.
        """
        css = _css(self._home())
        clean_markup = self._home({THEME_PARAM: CLEAN})

        self.assertIn(
            "display:none", _declaration_block(css, f".{CLEAN} #{SWITCH_ID}")
        )
        self.assertIn(f'id="{SWITCH_ID}"', clean_markup)
        self.assertIn(f">{LABELS[0]}</button>", clean_markup)
