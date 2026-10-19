"""Tests for the theme token layer and the class that selects a world.

A separate module from `tests.py` for the reason `test_hire_me_panel.py`
records: `tests.py` is already 802 lines and pylint's `too-many-lines` ceiling
is 1000, which this story's tests would cross. The story's Scope names
`tests.py` because it was written before that split; the split is the newer
decision and the one the repo actually follows.

What this module pins is one sentence: **the token layer is the only source of
colour**. A page that writes a hex literal, or a world that leaves a token
undefined, is Arcade showing through a world that is supposed to have replaced
it -- and it shows through looking deliberate, which is why it needs a test
rather than an eye.
"""

import re
from unittest.mock import patch

from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import reverse
from django.utils.html import strip_tags

from .api import PortfolioAPIError, PortfolioNotFoundError
from .context_processors import (
    ARCADE,
    CLEAN,
    DEFAULT_THEME,
    HORROR,
    MANOR,
    ROOT_CLASSES,
    THEME_PARAM,
    root_class,
)
from .tests import AVAILABILITY, PROJECT, PROJECTS, SKILLS

# The three worlds that ARE a class, in the order their blocks appear. Arcade
# is deliberately absent: it is the `:root` palette itself, spelled as the
# absence of a class, so "the worlds with a class block" excludes it.
THEMES = (MANOR, HORROR, CLEAN)

# The palette `:root` is expected to declare -- nine original plus the three
# promoted from literals that used to bypass the layer (the sticky nav
# backdrop, the hover border, the XP track). This list is documentation, and
# one test holds it to what `:root` actually declares so it cannot rot. The
# "is every world complete" test does NOT read it: that set is derived from
# real usage, because a hand-written list can only ever check itself.
TOKENS = (
    "--void", "--panel", "--line", "--neon", "--ember", "--gold",
    "--ice", "--text", "--muted", "--nav", "--line-hover", "--track",
)

# Arcade's nine, as the bytes they have always been. AC 2 is a regression
# guard on exactly this text: the token layer is built by ADDING blocks that
# override `:root`, never by editing `:root`, and an accidental edit here
# would re-palette all four worlds at once.
ARCADE_PALETTE = (
    "--void:#07070a", "--panel:#111118", "--line:#2a2a38",
    "--neon:#ff2d55", "--ember:#ff6b1a", "--gold:#ffc83d", "--ice:#22d3ee",
    "--text:#e8e8f0", "--muted:#8b8ba3",
)

# The templates a visitor can actually be served. `base.html` is excluded on
# purpose -- it IS the stylesheet, and the one file where colour may live.
PAGE_TEMPLATES = (
    "ui/home.html",
    "ui/project_detail.html",
    "ui/_project_grid.html",
    "ui/_signal_lost.html",
    "404.html",
)

STYLE_ATTRIBUTE = re.compile(r'style="([^"]*)"')
COLOUR_LITERAL = re.compile(r"#[0-9a-fA-F]{3}|rgba?\(")
VAR_USE = re.compile(r"var\((--[a-z-]+)\)")
TOKEN_DEF = re.compile(r"(--[a-z-]+)\s*:")

# A CSS rule, flattened: selector plus the declarations between its braces.
CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")

# CSS comments, stripped before any test DERIVES a set from the stylesheet's
# text. Not pedantry: the contract comment at the top of the block spells out
# the rule using the words `var(--token)`, and a usage scan that reads
# comments duly reported a token named `--token` missing from all four worlds.
COMMENT = re.compile(r"/\*.*?\*/", re.S)

# A pseudo-element that DRAWS itself, and so is decoration. Written tolerantly
# -- `content:''`, `content: ""` and the spaced forms are the same thing, and
# a guard that only recognises one spelling silently stops guarding the day
# someone writes another.
DRAWN = re.compile(r"content\s*:\s*(?:''|\"\")")

# The one line on the page that differs between two renders microseconds
# apart. Normalised before any "identical content" comparison, or the test
# fails roughly once a month, at a minute boundary, for no reason.
SYSTEM_TIME = re.compile(r"SYSTEM TIME :: [\d-]+ [\d:]+ UTC")


def _stylesheet(html):
    """The contents of `base.html`'s inline `<style>` block."""
    return html.split("<style>", 1)[1].split("</style>", 1)[0]


def _declaration_block(css, selector):
    """The declarations inside `selector{...}`, matched exactly.

    Exactly matters: a loose search for `.manor` also finds `.manor body` and
    `.manor .btn`, so a token test could pass on a declaration living in some
    other rule of the same world. Anchoring on `selector{` with the brace
    attached keeps "is this token defined in Manor's palette block" from
    quietly becoming "does Manor mention this token anywhere".
    """
    opening = f"{selector}{{"
    start = css.index(opening) + len(opening)
    end = css.index("}", start)
    return css[start:end]


def _rules_naming(css, class_name):
    """Every rule in `css` whose SELECTOR list mentions `.class_name`.

    `[^{}]*` cannot cross a brace, so a match is always one selector list and
    never a run of rules -- which is what makes counting these a count of
    RULES rather than of mentions. The word boundary keeps a search for one
    preference class off another whose name merely extends it.

    Shared by the two stories that hang a preference class on the root
    element: `test_effects.py` counts the stillness rules, `test_scares.py`
    the scare ones. Both ask the same question -- is this still ONE block, or
    has it grown into a per-animation list somebody has to maintain?
    """
    return re.findall(rf"[^{{}}]*\.{class_name}\b[^{{}}]*\{{", css)


def _world_join(css, class_name):
    """The first selector joining `.class_name` to a WORLD's class, or `None`.

    Built from `ROOT_CLASSES` rather than a typed list, so a fifth world
    tomorrow is checked without anyone remembering to add it. Arcade is
    skipped because its class is the empty string -- it IS `:root`, so there
    is no class to join.

    The mistake this catches is silent rather than ugly. `_declaration_block`
    locates a world's palette by its class name followed by an opening brace,
    so a rule joining a preference class to a world's would be found FIRST and
    read as that world's palette -- for every token the suite checks.
    """
    joined = "|".join(
        rf"\.{world}\b[^{{}}]*\.{class_name}\b|\.{class_name}\b[^{{}}]*\.{world}\b"
        for world in ROOT_CLASSES.values()
        if world
    )
    return re.search(joined, css)


def _without_comments(css):
    """The stylesheet with its comments removed, for scanning."""
    return COMMENT.sub("", css)


def _sections(css):
    """The stylesheet split into the base rules and one slice per world.

    The base rules are everything before the first theme block -- they apply
    in EVERY world, which is what makes the tokens they use universal.
    """
    marks = [(css.index(f".{name}{{"), name) for name in THEMES]
    marks.sort()
    bounds = [index for index, _ in marks] + [len(css)]
    sections = {"base": css[: bounds[0]]}
    for position, (start, name) in enumerate(marks):
        end = bounds[position + 1]
        sections[name] = css[start:end]
    return sections


def _colour_literals(markup):
    """Every `style="..."` in `markup` that writes a colour of its own.

    Returned rather than asserted so one call site can name WHICH attribute
    offends, in a template, a rendered page or a swapped fragment alike --
    the rule is one rule, and it was previously spelled out at three call
    sites that would each have had to change together.
    """
    return [style for style in STYLE_ATTRIBUTE.findall(markup) if COLOUR_LITERAL.search(style)]


def _root_tag(html):
    """The attributes of the opening `<html ...>` tag.

    Anchored on `<html` rather than on the first `>` in the document, because
    the first `>` closes `<!DOCTYPE html>` -- a slice that looks right, reads
    right, and silently tests the doctype instead of the root element.
    """
    return html.split("<html", 1)[1].split(">", 1)[0]


def _body_text(html):
    """The words a visitor reads, with markup and whitespace normalised away.

    Sliced to `<body>` so the comparison never sees the `<style>` block: the
    stylesheet is identical in every world anyway, and including it would let
    a genuine copy difference hide inside a few hundred lines of CSS.
    """
    body = html.split("<body>", 1)[1].split("</body>", 1)[0]
    return SYSTEM_TIME.sub("", " ".join(strip_tags(body).split()))


class ThemeResolverTests(SimpleTestCase):
    """`root_class` alone -- no HTTP, no template.

    The resolver is the one place a world name becomes a root class, so it is
    worth testing directly rather than only through a rendered page: these
    assertions are the whole contract US-5.3 inherits when it replaces the
    query parameter with a stored preference.
    """

    def test_each_world_resolves_to_its_own_class(self):
        """A world's class is its name."""
        self.assertEqual(root_class(MANOR), "manor")
        self.assertEqual(root_class(HORROR), "horror")
        self.assertEqual(root_class(CLEAN), "clean")

    def test_arcade_resolves_to_no_class_at_all(self):
        """Arcade is `:root`, so selecting it is selecting nothing.

        The empty string is not a miss -- it is Arcade's answer, and it is
        what makes an Arcade page render the byte-identical `<html lang="en">`
        it rendered before this story existed.
        """
        self.assertEqual(root_class(ARCADE), "")

    def test_an_unrecognised_name_falls_back_to_the_default(self):
        """A typo must not reach `<html>` as an undefined class.

        An undefined class raises nothing and logs nothing; it renders a page
        with no palette. The name arrives from a query parameter, so this is
        visitor-controlled input and the mapping doubles as the whitelist.
        """
        self.assertEqual(root_class("arcade-v2"), DEFAULT_THEME)
        self.assertEqual(root_class(""), DEFAULT_THEME)

    def test_no_name_at_all_falls_back_to_the_default(self):
        """`None` is what an absent query parameter yields.

        Pinned separately from the unrecognised-name case because the
        processor deliberately does NOT default at the `request.GET.get` call
        -- it passes `None` through so that "unknown becomes the default" is
        written in exactly one place. This test is what would fail if someone
        "helpfully" added the second copy back.
        """
        self.assertEqual(root_class(None), DEFAULT_THEME)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ThemeStylesheetTests(SimpleTestCase):
    """The stylesheet itself: the token set, and the discipline around it.

    These read the rendered CSS as text. There is no browser in the gate, and
    the acceptance criterion offers "a test or a documented check" precisely
    because of that -- so these are the mechanical half. What they cannot
    reach is anything that needs layout or the cascade resolved: those were
    checked in a browser and recorded in the story's Q4.
    """

    def _css(self):
        """The stylesheet as rendered on the home page."""
        return _stylesheet(self.client.get(reverse("ui:home")).content.decode())

    def test_root_declares_exactly_the_documented_palette(self, *_mocks):
        """`TOKENS` is documentation, so it is held to what `:root` declares.

        Without this, the list above could drift from the stylesheet and
        nothing would say so -- and every other test that mentions a token by
        name would still pass while documenting a palette that no longer
        exists.
        """
        declared = set(TOKEN_DEF.findall(
            _declaration_block(_without_comments(self._css()), ":root")
        ))

        self.assertEqual(declared, set(TOKENS))

    def test_every_token_the_shared_rules_use_is_defined_in_every_world(self, *_mocks):
        """AC 3: a token a world leaves out is Arcade leaking into it.

        The set is DERIVED, not typed out: every `var(--x)` read by a base
        rule or by a page template, both of which apply in all four worlds.
        A hand-written list can only ever check itself -- add a thirteenth
        token to a template tomorrow, define it in `:root` alone, and a
        list-driven test passes while three worlds silently render Arcade's
        value for it. This one fails.
        """
        css = _without_comments(self._css())
        sections = _sections(css)
        used = set(VAR_USE.findall(sections["base"]))
        for name in PAGE_TEMPLATES:
            used |= set(VAR_USE.findall(get_template(name).template.source))

        self.assertTrue(used, "no var() usage found -- the regex has drifted")
        for world in (ARCADE, *THEMES):
            block = _declaration_block(css, ":root" if world == ARCADE else f".{world}")
            defined = set(TOKEN_DEF.findall(block))
            with self.subTest(world=world):
                self.assertEqual(used - defined, set())

    def test_no_theme_rule_reads_a_token_its_world_never_defines(self, *_mocks):
        """AC 3, the other direction: a `var()` that resolves to nothing.

        A world-local property (Manor's `--lit`) is legitimate, but only in
        the world that declares it. This catches the rule that references one
        from a world where it does not exist -- which paints nothing at all,
        raises nothing, and logs nothing.
        """
        css = _without_comments(self._css())
        sections = _sections(css)
        root = set(TOKEN_DEF.findall(_declaration_block(css, ":root")))

        for world in THEMES:
            defined = root | set(TOKEN_DEF.findall(_declaration_block(css, f".{world}")))
            with self.subTest(world=world):
                self.assertEqual(set(VAR_USE.findall(sections[world])) - defined, set())

    def test_the_arcade_palette_is_unchanged(self, *_mocks):
        """AC 2: `:root` is Arcade, and this story did not edit it.

        Asserted as the literal bytes, because the failure this guards is a
        well-meaning tidy-up of `:root` -- which would silently re-palette
        every world at once, since the other three only override it.
        """
        root = _declaration_block(self._css(), ":root")

        for declaration in ARCADE_PALETTE:
            with self.subTest(declaration=declaration):
                self.assertIn(declaration, root)

    def test_page_templates_carry_no_colour_literals(self, *_mocks):
        """AC 3 and AC 10: colour lives in the stylesheet, nowhere else.

        This is the test that would have caught the defect this story fixed:
        the sticky nav hardcoded `rgba(7,7,10,.82)` in its `style` attribute,
        so it stayed Arcade-black in all four worlds while every token around
        it changed. Pinning the five page templates stops the next one.
        """
        offenders = {
            name: _colour_literals(get_template(name).template.source)
            for name in PAGE_TEMPLATES
        }

        self.assertEqual({name: found for name, found in offenders.items() if found}, {})

    def test_just_the_work_suppresses_the_overlays(self, *_mocks):
        """AC 4: "No blood, no creatures, nothing that moves."

        Suppressed, not recoloured -- a fainter scanline is still a scanline,
        and Just the Work is the world defined by absence. The base overlays
        must survive: Clean withdraws them for itself, it does not delete
        them for everyone.
        """
        css = self._css()
        clean = _sections(css)[CLEAN]

        overlays = _declaration_block(clean, ".clean body::before,.clean body::after")
        self.assertIn("display:none", overlays)
        self.assertIn("animation:none", _declaration_block(clean, ".clean .flicker"))
        for overlay in ("body::before", "body::after"):
            with self.subTest(overlay=overlay):
                self.assertIn(f"\n  {overlay}{{", css)

    def test_every_decorative_pseudo_element_is_click_transparent(self, *_mocks):
        """AC 7 (NFR-8): nothing decorative may intercept a click.

        Keyed on drawing itself rather than on a list of selectors, so the
        rule binds whatever epic 6 adds next: a pseudo-element with `content`
        is decoration, and decoration does not take clicks. The corner
        brackets on `.hud` were the one that did not carry it.
        """
        drawn = [
            (selector, body)
            for selector, body in CSS_RULE.findall(self._css())
            if DRAWN.search(body)
        ]

        self.assertTrue(drawn, "no drawn pseudo-elements found -- the regex has drifted")
        for selector, body in drawn:
            with self.subTest(selector=selector.strip()):
                self.assertIn("pointer-events:none", body)

    def test_each_world_loads_its_display_face(self, *_mocks):
        """The two extra faces are requested, or two worlds render in Arcade's.

        One `<link>`, four families. `Press+Start+2P` is asserted alongside
        the new two because an edit that replaced the href rather than
        extending it would otherwise pass.
        """
        html = self.client.get(reverse("ui:home")).content.decode()

        self.assertIn("Press+Start+2P", html)
        self.assertIn("Special+Elite", html)
        self.assertIn("IM+Fell+English+SC", html)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class ThemeApplicationTests(SimpleTestCase):
    """The class actually reaching `<html>`, on every page a visitor can hit."""

    detail_url = reverse("ui:project-detail", kwargs={"slug": "subscription-platform"})

    def _root(self, url, theme=None):
        """The opening `<html>` tag of `url`, rendered in `theme`."""
        query = {THEME_PARAM: theme} if theme else {}
        return _root_tag(self.client.get(url, query).content.decode())

    def test_a_world_classes_the_root_element(self, *_mocks):
        """AC 1: one class on the root is the whole mechanism."""
        for world in THEMES:
            with self.subTest(world=world):
                self.assertEqual(
                    self._root(reverse("ui:home"), world), f' lang="en" class="{world}"'
                )

    def test_the_default_world_is_haunted_manor(self, *_mocks):
        """BRD S2's world table: Manor is what an unchosen visitor gets."""
        self.assertEqual(self._root(reverse("ui:home")), ' lang="en" class="manor"')

    def test_arcade_renders_no_class_at_all(self, *_mocks):
        """AC 2: the unthemed page is today's page, down to the tag.

        Not "a class that happens to look like Arcade" -- no class. The
        equality is against the bare attribute, so an empty `class=""` would
        fail it too.
        """
        self.assertEqual(self._root(reverse("ui:home"), ARCADE), ' lang="en"')

    @patch("ui.views.fetch_project", return_value=PROJECT)
    def test_the_detail_page_carries_the_world(self, *_mocks):
        """AC 1: the theme dresses every page, not just the one with the nav."""
        self.assertEqual(self._root(self.detail_url, HORROR), ' lang="en" class="horror"')

    @patch("ui.views.fetch_project", side_effect=PortfolioNotFoundError("gone"))
    def test_the_404_carries_the_world(self, *_mocks):
        """AC 1, and the reason the mechanism is a context processor.

        `404.html` is rendered by Django's own `page_not_found`, which no view
        of ours controls. A theme passed from a view would reach the three
        pages we render and drop a visitor who mistyped a URL back into
        Arcade. This assertion is what makes that structural rather than
        remembered.
        """
        response = self.client.get(self.detail_url, {THEME_PARAM: CLEAN})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(_root_tag(response.content.decode()), ' lang="en" class="clean"')

    def _grid(self, category):
        """The fragment HTMX swaps into `#grid` for `category`."""
        url = reverse("ui:project-grid")
        return self.client.get(url, {"category": category}).content.decode()

    def test_the_htmx_fragment_cannot_touch_the_root_class(self, *_mocks):
        """AC 5 (flag F12): the swapped fragment carries no root of its own.

        Safe by construction -- the class is on `<html>` and HTMX replaces
        only `#grid`'s contents -- and pinned because "safe by construction"
        is a property of TODAY's construction. A refactor that gave the
        partial its own wrapper class, or let it extend `base.html`, would
        break theming on every category click and nothing else would notice.

        What a server-side test can prove is that the fragment contains no
        root element and no competing theme class. That the live swap keeps
        the world was checked in a browser, in all four worlds, by clicking a
        category and reading the new card's computed border colour back.
        """
        fragment = self._grid("Blog")

        self.assertNotIn("<html", fragment)
        self.assertNotIn("<body", fragment)
        for world in THEMES:
            with self.subTest(world=world):
                self.assertNotIn(f'class="{world}"', fragment)

    def test_the_swapped_grid_reaches_colour_only_through_tokens(self, *_mocks):
        """AC 5 and AC 6: the fragment inherits the world rather than naming it.

        The partial cannot carry the root class, so the ONLY way its cards
        come out in the active world is by reaching colour through tokens and
        themed classes. A hex literal here would be a card that stays Arcade
        after every category click -- the nav defect again, one level down.
        """
        fragment = self._grid("Blog")

        self.assertIn('class="card hud', fragment)
        self.assertIn("var(--", fragment)
        self.assertEqual(_colour_literals(fragment), [])

    def test_the_no_entries_panel_reaches_colour_only_through_tokens(self, *_mocks):
        """AC 6: the empty-category state is themed too.

        It renders inside the swapped fragment, which has no root class, so
        what makes it "in the active world" is that it names themed classes
        and tokens and never a colour of its own. Its wording is untouched:
        US-5.1 settled one vocabulary across four palettes.
        """
        fragment = self._grid("Nothing")

        self.assertIn("// NO ENTRIES", fragment)
        self.assertIn('class="hud', fragment)
        self.assertIn("gold-text", fragment)
        self.assertEqual(_colour_literals(fragment), [])

    def test_content_is_identical_across_worlds(self, *_mocks):
        """AC 8 (F-18): a theme changes the palette, never the words.

        Two assertions, deliberately. The first is the acceptance criterion as
        written -- the visible text of two worlds is the same. The second is
        stronger and is what actually protects F-18: swap one world's class
        for the other's and the two documents are byte-identical, so a theme
        cannot have changed a heading, an attribute or an element either.
        """
        clean = self.client.get(reverse("ui:home"), {THEME_PARAM: CLEAN}).content.decode()
        horror = self.client.get(reverse("ui:home"), {THEME_PARAM: HORROR}).content.decode()

        self.assertEqual(_body_text(clean), _body_text(horror))
        self.assertEqual(
            SYSTEM_TIME.sub("", clean).replace('class="clean"', 'class="horror"'),
            SYSTEM_TIME.sub("", horror),
        )


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
class ThemeOutageTests(SimpleTestCase):
    """The degraded page is still the site, so it still wears the world.

    A separate class for the reason `HomeViewOutageTests` is one: the fetch
    these tests need to FAIL cannot also be patched at class level, because
    the class decorator is applied last and would win. Only the availability
    patch -- which no test here overrides -- lives up here.
    """

    @patch("ui.views.fetch_skills", side_effect=PortfolioAPIError("down"))
    @patch("ui.views.fetch_projects", side_effect=PortfolioAPIError("down"))
    def test_signal_lost_renders_in_the_active_world(self, *_mocks):
        """AC 6: the outage panel is themed, and its wording is untouched.

        The panel a visitor sees when the backend is away is still the site,
        so it wears the world they chose. Asserting the copy alongside the
        class pins both halves of US-5.1's decision in one place: the palette
        changes between worlds, the words do not.
        """
        response = self.client.get(reverse("ui:home"), {THEME_PARAM: CLEAN})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "// SIGNAL LOST")
        self.assertEqual(_root_tag(response.content.decode()), ' lang="en" class="clean"')
