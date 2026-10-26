"""Tests for the preference store and the portfolio that does not need it.

A separate module for the reason `test_theme.py` and `test_hire_me_panel.py`
record: `tests.py` is already 802 lines against pylint's `too-many-lines`
ceiling of 1000. The story's Scope names `tests.py` because it was written
before that split; the split is the newer decision and the one the repo
follows.

**Django cannot execute JavaScript.** `SimpleTestCase` renders templates; it
does not run them. So these tests deliberately do NOT try to prove that the
store works -- they prove the two things a server-side suite genuinely can,
and they are the two that matter most:

1. **The script is there, and shaped the way NFR-7 requires** -- every storage
   access inside a `try`, no console noise, the vocabulary rendered from
   Python rather than spelled a second time in JavaScript.
2. **The page never needed it.** With every `<script>` removed, the portfolio
   is still a navigable portfolio (**A1**). That is the more important
   property of the two, and the only one a visitor with JavaScript off
   experiences.

The branching itself -- unknown values, storage that throws, the
reduced-motion default -- was exercised by running the RENDERED script against
a fake DOM under Node, and by hand in a private window. Both are recorded in
the story's Implementation notes, because neither can live in this file.
"""

import json
import re
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from .api import PortfolioNotFoundError
from .context_processors import CLEAN, ROOT_CLASSES, THEME_PARAM
from .tests import AVAILABILITY, CONTACT_HREF, PITCH_LINE, PROJECT, PROJECTS, SKILLS

# The mockup's three keys, unchanged by this story so that a visitor who saw
# the mockup and then the site keeps their choice. Pinned as a set because
# their ORDER in the script is a style question, but their presence is not.
KEYS = ("axe.theme", "axe.motion", "axe.scares")

# The owned inline script -- the one with no `src` and no `type`. Anchored
# that way so neither the HTMX tag nor the `json_script` block can be mistaken
# for it; the `json_script` block in particular is a `<script>` element too,
# which is the trap this pattern avoids.
OWNED_SCRIPT = re.compile(r"<script>(.*?)</script>", re.S)

# Everything in `<head>` that makes the parser wait, named by a fragment of
# its tag. The store must come above all of them (AC 9) -- see the test for
# why this is a set rather than one named tag.
RENDER_BLOCKING = (
    "unpkg.com/htmx.org",
    "fonts.googleapis.com/css2",
    "<style>",
    "ui/tailwind.css",
)

# Every script element of any kind, for the JavaScript-off simulation.
ANY_SCRIPT = re.compile(r"<script\b[^>]*>.*?</script>", re.S)

# The vocabulary block `json_script` emits.
WORLDS_JSON = re.compile(
    r'<script id="theme-worlds" type="application/json">(.*?)</script>', re.S
)

DETAIL_URL = reverse("ui:project-detail", kwargs={"slug": PROJECT["slug"]})


def _inline_script(html, marker):
    """The one owned inline script whose source contains `marker`.

    Parameterised because this package now reads two of them -- the store and
    US-5.4's chooser -- and "find the attribute-less `<script>` that is this
    one, and assert there is exactly one of it" is the same job both times.
    The marker is the only thing that differs, so the marker is the argument.
    """
    found = [block for block in OWNED_SCRIPT.findall(html) if marker in block]
    assert len(found) == 1, f"expected one script matching {marker!r}, found {len(found)}"
    return found[0]


def _owned_script(html):
    """The preference STORE's source, which must be exactly one element.

    Anchored on `window.axePrefs =`, the line that DEFINES the API, rather
    than on the name `axePrefs` anywhere in the block. The distinction became
    load-bearing the moment US-5.4 added a second inline script: the chooser
    calls `window.axePrefs.setWorld`, so a filter on the bare name matches it
    too and every assertion below starts reading whichever block the regex
    reached first. US-5.5 and US-5.6 add two more callers.

    The definition is the right anchor because there is exactly one of it, by
    the same rule that makes this helper worth having: the store is the one
    place storage is touched, so it is the one place the API is created.
    """
    return _inline_script(html, "window.axePrefs =")


def _code_lines(script):
    """`script`'s lines with the `//` commentary dropped.

    The guard test below counts how many lines reach storage, and the script's
    comments explain at length why storage is dangerous -- so a comment that
    merely says the word would read as a third, unguarded access and fail a
    test about code that never changed.
    """
    return [line for line in script.splitlines() if not line.strip().startswith("//")]


def _render_every_page(client):
    """Home, a project page and a 404 -- the three renders of `base.html`.

    Shared because the reason to run a test over all three is shared, and it
    is not obvious: `base.html` has three renderers and one of them is not
    ours. Django's own `page_not_found` builds the 404, reaching the template
    through the context processor alone, so anything wired into a view is
    present on two pages and absent on the third -- the page a visitor
    reaches by mistake, and the one they most need a way out of.

    A function taking the client rather than a mixin: the test classes that
    want it already carry three `@patch` decorators, and a fourth inherited
    from a base class is the kind of stacking that makes a failure hard to
    read.
    """
    with patch("ui.views.fetch_project", return_value=PROJECT):
        pages = {
            "home": client.get(reverse("ui:home")).content.decode(),
            "detail": client.get(DETAIL_URL).content.decode(),
        }
    with patch("ui.views.fetch_project", side_effect=PortfolioNotFoundError("gone")):
        pages["404"] = client.get(DETAIL_URL).content.decode()
    return pages


def _assert_work_survives_without_scripts(case, html):
    """Every project title is still on `html` once the scripts are stripped.

    A1, and every story that adds a fixed, always-on-screen element asserts
    it -- the stillness control (US-5.5) and the scares switch (US-5.6) so
    far -- because each one adds the same risk: a page that quietly stops
    being readable for a visitor who cannot dismiss what floats over it.

    ONE definition, called from each of those suites, rather than the same
    three lines written out in each. A function taking the case rather than a
    mixin, for the reason `_render_every_page` records: the classes that want
    it already carry three `@patch` decorators, and a fourth inherited from a
    base class makes a failure hard to read.
    """
    for project in PROJECTS:
        with case.subTest(project=project["slug"]):
            case.assertIn(project["title"], html)


def _without_scripts(html):
    """`html` as a visitor with JavaScript disabled receives it.

    Removing the elements is a closer simulation than it looks: an inert
    `hx-get` attribute left behind changes nothing a reader can see, whereas a
    `<script>` that was carrying content would vanish -- which is precisely
    the failure A1 forbids and this helper exposes.
    """
    return ANY_SCRIPT.sub("", html)


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class PreferenceScriptTests(SimpleTestCase):
    """The script's presence and shape -- the half a template render can see."""

    def _home(self, query=None):
        """The home page's HTML, optionally pinned to a world."""
        return self.client.get(reverse("ui:home"), query or {}).content.decode()

    def test_the_script_is_present_on_every_page(self, *_mocks):
        """AC 8, on all three renders -- including the one no view of ours owns.

        The 404 is the reason this is asserted per page rather than once. It is
        rendered by Django's own `page_not_found`, so it reaches `base.html`
        through the context processor alone; a preference mechanism wired into
        a view would be absent exactly there, and a visitor who mistyped a URL
        would lose their world on the way back.

        That reason is why `_render_every_page` exists, and this test is a
        caller of it like the others. It was the original copy, and leaving it
        hand-rolled here would have left the knowledge in two places in the one
        module that defines the helper -- so a change to how the 404 is reached
        would need finding twice.
        """
        for name, html in _render_every_page(self.client).items():
            with self.subTest(page=name):
                script = _owned_script(html)
                for key in KEYS:
                    self.assertIn(key, script)

    def test_the_script_runs_before_everything_render_blocking(self, *_mocks):
        """AC 9: the before-paint decision, pinned structurally rather than remembered.

        The class must be corrected before the browser paints, which is what
        makes a returning Found Footage visitor's page never flash candlelight.
        Being in `<head>` is what delivers that -- nothing is painted while
        `<head>` is still parsing. Being ABOVE every render-blocking tag is
        the second half: each one makes the parser wait, so a script placed
        after any of them waits on a fetch before setting a class it already
        knows. An edit that moves it below one is silent in every test but
        this, and visible to a visitor as a flash.

        Asserted against the whole set rather than a named tag. US-7.2 deleted
        the third-party script that used to be first in it, and a test naming
        that one tag would have gone green by losing its subject -- the
        ordering rule outlived the tag, so the test is written against the
        rule. A blocking tag added tomorrow belongs in this tuple.
        """
        head = self._home().split("</head>", 1)[0]
        first = head.index("axePrefs")

        for tag in RENDER_BLOCKING:
            with self.subTest(tag=tag):
                self.assertIn(tag, head, f"{tag} is no longer in <head>; fix the tuple")
                self.assertLess(first, head.index(tag))

    def test_the_world_vocabulary_is_rendered_from_the_resolver(self, *_mocks):
        """AC 4: one definition of what a world is, and it is Python's.

        The script validates a stored value against this mapping and reads the
        class out of it, so a hand-written copy in JavaScript would be a second
        whitelist free to drift from `ROOT_CLASSES`. The symptom of that drift
        is not an error -- it is a page with no palette, or a world that
        silently stops being selectable.

        Asserted as the whole mapping, not just its keys: Arcade's class is the
        empty string, and a names-only list could not carry it.
        """
        rendered = WORLDS_JSON.search(self._home())

        self.assertIsNotNone(rendered, "the vocabulary block is missing")
        self.assertEqual(json.loads(rendered.group(1)), ROOT_CLASSES)

    def test_every_storage_access_is_guarded(self, *_mocks):
        """AC 2 (NFR-7): an unhandled throw here is a blank page, not a portfolio.

        Three assertions, because the rule has three halves that fail
        differently. Storage is reached exactly twice, so there is no third
        access that skipped the discipline. Each of those lines carries its own
        `try`. And each spells `window.localStorage`, because the throw happens
        on the PROPERTY ACCESS in a private window, not only on the call -- a
        bare `localStorage.getItem` inside a `try` would be guarded by
        accident and a reader would not see why it had to be.
        """
        script = _owned_script(self._home())
        touching = [line for line in _code_lines(script) if "localStorage" in line]

        self.assertEqual(len(touching), 2, f"expected two storage accesses, got {touching}")
        for line in touching:
            with self.subTest(line=line.strip()):
                self.assertIn("try {", line)
                self.assertIn("window.localStorage", line)

    def test_the_script_never_logs(self, *_mocks):
        """AC 2: the catch is silent, and that is correct here and only here.

        A visitor who has blocked site data would otherwise meet a console
        error on every page load of every visit -- noise forever, for a
        condition the site handles completely. The one honest behaviour is to
        fall back to the default and carry on.
        """
        self.assertNotIn("console.", _owned_script(self._home()))

    def test_matchmedia_is_guarded_too(self, *_mocks):
        """`matchMedia` is tested for before it is called.

        It exists everywhere relevant, so this looks like superstition until
        you notice where the script runs: first in `<head>`, before anything
        else on the page. Whatever it throws, it throws before the portfolio
        exists. The defensive form costs one `&&`.

        Whitespace is collapsed before matching so that re-wrapping the line
        cannot fail a test about a guard that is still there. What is pinned
        is the `&&`, which is the whole assertion.
        """
        collapsed = " ".join(_owned_script(self._home()).split())

        self.assertIn("window.matchMedia && window.matchMedia(", collapsed)

    def test_a_pinned_render_tells_the_script_so(self, *_mocks):
        """The `?theme=` QA override survives this story (US-5.2's Q3).

        The server knows whether the URL asked for a world; the client would
        have to re-parse `location.search` to find out, which would put a
        second reader of the query parameter in the codebase. So the server
        says, and the script's first guard obeys. Without this, a tester with
        a world stored would be handed their own world instead of the one they
        asked for -- and the override would look broken rather than overridden.
        """
        self.assertIn("var pinned = true;", _owned_script(self._home({THEME_PARAM: CLEAN})))
        self.assertIn("var pinned = false;", _owned_script(self._home()))


@patch("ui.views.fetch_availability", return_value=AVAILABILITY)
@patch("ui.views.fetch_skills", return_value=SKILLS)
@patch("ui.views.fetch_projects", return_value=PROJECTS)
class NoJavaScriptTests(SimpleTestCase):
    """AC 7 (A1): with JavaScript off, the site is still a navigable portfolio.

    The store is the first JavaScript this site owns, which makes this the
    moment the no-JavaScript property stops being free and starts needing a
    guard. Every assertion here runs against the page with every `<script>`
    element removed.
    """

    def _stripped_home(self):
        """The home page as a visitor with JavaScript disabled receives it."""
        return _without_scripts(self.client.get(reverse("ui:home")).content.decode())

    def test_every_project_is_reachable_without_script(self, *_mocks):
        """A1's load-bearing half: the work is the point of the site.

        Each project is a plain `<a href>` row rendered server-side into the
        grid, so this passes today by construction -- and "by construction" is
        a property of TODAY's construction. A later story that moved the grid
        behind an HTMX load, or hid it pending the chooser, would take every
        project off the page for a visitor with JavaScript off and nothing
        else would notice.
        """
        html = self._stripped_home()

        for project in PROJECTS:
            with self.subTest(project=project["slug"]):
                self.assertIn(reverse("ui:project-detail", kwargs={"slug": project["slug"]}), html)
                self.assertIn(project["title"], html)

    def test_every_section_reads_without_script(self, *_mocks):
        """A1's other half: the sections are readable and the nav still points at them."""
        html = self._stripped_home()

        self.assertIn(PITCH_LINE, html)
        self.assertIn(CONTACT_HREF, html)
        for anchor in ("#about", "#projects", "#contact"):
            with self.subTest(anchor=anchor):
                self.assertIn(f'href="{anchor}"', html)

    @patch("ui.views.fetch_project", return_value=PROJECT)
    def test_a_project_page_reads_without_script(self, *_mocks):
        """A case study is prose and a server render; nothing about it needs a script."""
        html = _without_scripts(self.client.get(DETAIL_URL).content.decode())

        self.assertIn(PROJECT["title"], html)
        self.assertIn(PROJECT["problem"], html)

    def test_the_default_world_is_server_rendered(self, *_mocks):
        """AC 6: Haunted Manor arrives on `<html>` without the script's help.

        This is what makes "do nothing" the correct fallback for an
        unrecognised stored value: the default is already on the element
        before any JavaScript runs, so the script carries no copy of
        `DEFAULT_THEME` to drift from the server's.
        """
        html = self._stripped_home()

        self.assertIn('<html lang="en" class="manor">', html)
