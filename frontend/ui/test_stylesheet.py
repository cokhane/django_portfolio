"""Tests for the compiled stylesheet that replaced the CDN build (US-7.2).

A separate module for the reason `test_theme.py` records: `tests.py` is
already past 840 lines against pylint's 1000-line ceiling, so a story's tests
get their own file.

What this module pins is one sentence: **the utilities come from a committed
file the templates are proven against, and nothing third-party executes
without a hash.**

The guard that matters most is not the one-line removal of the `<script>` --
that is obvious in a diff and hard to undo by accident. It is
`test_every_class_the_templates_use_is_defined_somewhere`. A committed
generated file is only safe while it still covers the markup, and the two
ways it silently stops covering it are both invisible to every other test
here: a template the generator's scan never read, and a utility class that is
only ever applied from JavaScript. Both render an element with a class that
styles nothing, and Django tests assert content, not appearance -- so the page
looks broken to a visitor and correct to the suite. That test is what makes
regenerating this file by hand a safe thing to do.
"""

import re
from pathlib import Path
from unittest.mock import patch

from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import SimpleTestCase

from .test_preferences import _render_every_page
from .test_theme import _stylesheet, _without_comments
from .tests import AVAILABILITY, PROJECTS, SKILLS

# The host the story exists to remove. Named once, here, so the guard and its
# failure message cannot disagree about what they are looking for.
CDN_HOST = "cdn.tailwindcss.com"

# Where `{% static %}` resolves the sheet, and the version that generated it.
# The version is asserted rather than merely recorded: the defect this story
# fixed was an UNVERSIONED stylesheet, so a committed file that cannot say
# what built it would have kept half of it. An upgrade changes this line, on
# purpose -- that is a decision worth a diff.
SHEET_STATIC_PATH = "ui/tailwind.css"
SHEET_VERSION = "v3.4.17"

TEMPLATES = Path(__file__).resolve().parent / "templates"

# A floor, not a count. It stops a broken extractor from passing the coverage
# test by extracting nothing -- the one failure mode a set-difference
# assertion cannot report on its own, because the empty set is a subset of
# everything. 100 sits well under the 141 tokens the templates carry today, so
# ordinary editing never trips it.
MINIMUM_CLASS_TOKENS = 100

CLASS_ATTRIBUTE = re.compile(r'class="([^"]*)"')
TEMPLATE_MARKUP = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)
CLASS_TOKEN = re.compile(r"^[a-z][a-z0-9:/.-]*$")
CSS_CLASS_SELECTOR = re.compile(r"\.((?:[a-z0-9_-]|\\.)+)", re.I)
EXTERNAL_SCRIPT = re.compile(r'<script\b[^>]*\bsrc="https?://[^>]*>')

# A class a script applies, rather than one the server renders -- the half of
# the markup the stylesheet generator's scan cannot see.
SCRIPT_CLASS_CALL = re.compile(r"classList\.\w+\(([^)]*)\)")
STRING_LITERAL = re.compile(r'"([^"]*)"')

# Script-applied classes whose name is COMPUTED, so no scan of the script text
# can recover it, and where each is actually guarded instead. This list is the
# manual half of the dynamic-class invariant (AC 6) and is written down because
# the automatic half provably cannot reach it.
#
#   worlds[...]  -> `manor`, `horror`, `clean`, rendered from ROOT_CLASSES.
#                   test_preferences pins the rendered mapping against the
#                   Python one; test_theme pins that each world has a block.
#   STRUCK       -> `struck`, a module-level var in the same script.
COMPUTED_SCRIPT_CLASSES = ("manor", "horror", "clean", "struck")


def _template_files():
    """Every template in this app -- the one list all the walks below share."""
    return sorted(TEMPLATES.rglob("*.html"))


def _lines_naming(needle):
    """Every `file:line` whose text contains `needle`, across the templates."""
    return [
        f"{path.relative_to(TEMPLATES)}:{number}"
        for path in _template_files()
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if needle in line
    ]


def _class_tokens(markup):
    """The class names a template APPLIES, in one pass over its text.

    Django markup is replaced by a space rather than deleted: removing
    `{% if x %}` from `a{% if x %}b{% endif %}` would weld `a` and `b` into a
    token that appears nowhere in the rendered page, and the coverage test
    would then demand a rule for a class that does not exist.
    """
    attributes = CLASS_ATTRIBUTE.findall(TEMPLATE_MARKUP.sub(" ", markup))
    return {token for token in " ".join(attributes).split() if CLASS_TOKEN.match(token)}


def _script_class_literals(markup):
    """Class names a script applies as a literal, e.g. `classList.toggle("x")`.

    Literals only. A name the script COMPUTES -- `classList.add(worlds[name])`,
    `classList.add(STRUCK)` -- is invisible here and deliberately left so:
    inferring the value behind a variable would make this helper lie about
    what it has checked. `COMPUTED_SCRIPT_CLASSES` names those instead.
    """
    arguments = " ".join(SCRIPT_CLASS_CALL.findall(markup))
    return {name for name in STRING_LITERAL.findall(arguments) if CLASS_TOKEN.match(name)}


def _selector_classes(css):
    """The class names a stylesheet DEFINES, comments excluded.

    Comments are stripped for the reason `test_theme` strips them, running
    the other way: a class named only in prose styles nothing, and counting
    it as defined would let the coverage test pass for the wrong reason --
    which is precisely the reason that test exists.

    Tailwind escapes the colon and slash in a variant (`sm\\:text-lg`), so the
    backslashes come out before the name is compared to what markup applies.

    It over-includes: a decimal in a declaration (`gap: 0.5rem`) looks like a
    selector, so `5rem` joins the set. Harmless in the one direction this is
    read -- the set is only ever subtracted FROM what markup applies, so
    surplus entries can mask a real miss only if someone names a class after
    a number. Tightening it would mean parsing CSS rather than scanning it.
    """
    return {
        match.replace("\\", "")
        for match in CSS_CLASS_SELECTOR.findall(_without_comments(css))
    }


def _compiled_sheet():
    """The committed stylesheet, read from where `{% static %}` resolves it."""
    found = finders.find(SHEET_STATIC_PATH)
    assert found, f"{SHEET_STATIC_PATH} is not on the static path"
    return Path(found).read_text(encoding="utf-8")


class CdnRemovalTests(SimpleTestCase):
    """AC 1 and AC 9: the development-only build is gone, and stays gone.

    Asserted over the template FILES rather than a rendered page. The host
    appeared in a prose comment as well as in the `<script>` it described,
    and a comment is invisible to a render -- so a test reading HTML would
    have reported the hostname absent while it was still written in the
    source the next developer reads.
    """

    def test_no_template_names_the_development_cdn(self):
        """The one-line removal, pinned so it cannot quietly come back."""
        offenders = _lines_naming(CDN_HOST)

        # A guard that scans nothing passes for the wrong reason.
        self.assertGreater(len(_template_files()), 1, f"no templates under {TEMPLATES}")
        self.assertEqual(
            offenders,
            [],
            f"{CDN_HOST} is development-only and unversioned; the compiled "
            f"{SHEET_STATIC_PATH} replaces it. Offending lines: " + ", ".join(offenders),
        )

    def test_the_stylesheet_is_committed_and_records_what_generated_it(self):
        """A committed asset that cannot name its version repeats the defect."""
        sheet = _compiled_sheet()

        self.assertTrue(sheet.startswith("/*!"), "the sheet lost its provenance header")
        self.assertIn(SHEET_VERSION, sheet)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class CompiledStylesheetTests(SimpleTestCase):
    """What the server actually sends, on every page a visitor can reach."""

    def test_every_page_links_the_sheet_after_the_inline_stylesheet(self, *_mocks):
        """AC 2, and the cascade rule the swap turns on.

        The CDN build appended its `<style>` to the end of `<head>`, so the
        utilities have always come last. On Arcade -- the one world that is
        `:root` rather than a class -- `.display` and `.text-sm` are both
        single-class selectors and tie on specificity, so the utility wins
        only by being later. A link moved above the inline block flips that
        tie and changes every heading's line-height on every Arcade page,
        which no assertion about content can see. Hence the ordering is
        asserted, not just the presence.
        """
        expected = f'<link rel="stylesheet" href="{static(SHEET_STATIC_PATH)}">'

        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                self.assertIn(expected, html)
                self.assertLess(html.index("</style>"), html.index(expected))

    def test_every_class_the_page_applies_is_defined_somewhere(self, *_mocks):
        """AC 4 and AC 6: the content scan's OUTCOME, not its configuration.

        The story asks for every template to be in the scan, and for the
        dynamic-class hazard to be checked. Both are the same question asked
        twice -- does a class a visitor's browser sees actually have a rule? --
        so both are answered by deriving the set rather than maintaining a
        list. A template added tomorrow is walked because it is on disk.

        TWO sources, because the generator only reads one of them. It scans
        `class="..."` attributes, so a class applied from script is invisible
        to it and would be left out of the sheet. Markup alone would therefore
        have made this test agree with the generator instead of checking it.

        What this does NOT reach, stated plainly rather than implied: a class
        whose name the script COMPUTES. `classList.add(worlds[name])` and
        `classList.add(STRUCK)` hold no literal to read, so no scan of the
        script text can recover them. Those four are `COMPUTED_SCRIPT_CLASSES`
        above, which the next test holds to the same standard by name.
        """
        used = set()
        for path in _template_files():
            markup = path.read_text(encoding="utf-8")
            used |= _class_tokens(markup) | _script_class_literals(markup)

        home = _render_every_page(self.client)["home"]
        defined = _selector_classes(_stylesheet(home)) | _selector_classes(_compiled_sheet())
        missing = sorted(used - defined)

        self.assertGreater(
            len(used), MINIMUM_CLASS_TOKENS, "the class extractor found almost nothing"
        )
        self.assertEqual(
            missing,
            [],
            "these classes are applied in a template but defined nowhere; "
            "regenerate the sheet (README, 'Regenerating the stylesheet'): " + ", ".join(missing),
        )

    def test_the_computed_script_classes_are_defined_too(self, *_mocks):
        """AC 6's other half -- the classes no scan of the script can recover.

        The test above derives its set and so cannot name these. This one
        names them, which is the honest trade: a hand-written list can only
        ever check itself, but a list that checks SOMETHING beats a derived
        set that silently excludes it. The failure this guards is real and
        cheap to cause -- rename `.manor` in the stylesheet and the world
        still applies the old class, so the page renders unstyled while every
        content assertion in the suite stays green.
        """
        home = _render_every_page(self.client)["home"]
        defined = _selector_classes(_stylesheet(home)) | _selector_classes(_compiled_sheet())

        for name in COMPUTED_SCRIPT_CLASSES:
            with self.subTest(css_class=name):
                self.assertIn(name, defined)

    def test_every_external_script_carries_an_integrity_hash(self, *_mocks):
        """AC 8: nothing third-party executes unverified.

        The removed build could not satisfy this at all -- it was unversioned,
        so there was no fixed byte string to hash. What is left is HTMX, which
        is pinned and hashed. The webfont `<link>`s are deliberately out of
        scope: a stylesheet Google varies by user agent has no stable hash to
        pin, and the story's notes record self-hosting as the follow-up.
        """
        home = _render_every_page(self.client)["home"]
        tags = EXTERNAL_SCRIPT.findall(home)
        unhashed = [tag for tag in tags if 'integrity="sha' not in tag]

        self.assertGreater(len(tags), 0, "no external script found; has the markup moved?")
        self.assertEqual(unhashed, [], f"external scripts without an integrity hash: {unhashed}")
