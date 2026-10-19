"""The theme class every template render reads.

A context processor rather than a value each view passes, because `base.html`
has FIVE renderers and one of them is not ours: Django's own `page_not_found`
renders `404.html`, which extends `base.html`. A view-supplied value reaches
three of the five and leaves the 404 unthemed -- a visitor who mistypes a URL
would drop out of their chosen world onto an Arcade page. Django builds a
`RequestContext` for that render, so a processor reaches it with no custom
`handler404` and no repetition at three call sites.

The resolver and the request-side source are deliberately TWO functions.
`root_class` is pure and knows nothing about HTTP; `theme` is the only line in
the codebase that knows a world name arrives as a query parameter.

US-5.2 predicted that US-5.3 would REPLACE that line with a stored preference.
It did not, and the correction is worth recording rather than leaving the next
reader to wonder which document is stale: a preference lives in `localStorage`,
which the server cannot read at render time. So the query parameter stays
exactly as it was -- the permanent QA override -- and the stored world is
applied by the inline script in `base.html`, after this render and before the
browser paints. What US-5.3 added here is not a new SOURCE but the two values
that script needs and must not invent for itself.
"""

from django.http import HttpRequest

# The SERVER's only source of a world name, and now permanently so. US-5.2
# expected US-5.3 to replace this with a stored preference; US-5.3 instead put
# the preference on the client, where storage actually lives, so this never
# was the scaffolding it looked like. What it is is the QA override: the way
# to reach a named world with no stored state, which is what the by-hand pass
# across all four worlds depends on. A render it pins is left alone by the
# preference script in `base.html` and writes nothing to storage.
THEME_PARAM = "theme"

# The four worlds (BRD S11). Named rather than written inline because a typo
# in a bare string would silently become an unrecognised name -- which
# resolves to the default and looks like a working page, the hardest kind of
# mistake to see. `MANOR` is also read by `DEFAULT_THEME` below.
ARCADE = "arcade"
MANOR = "manor"
HORROR = "horror"
CLEAN = "clean"

# Haunted Manor for a visitor who has not chosen (BRD S2's world table).
DEFAULT_THEME = MANOR

# The one place a world name becomes a root class, and simultaneously the
# whitelist of names that mean anything. Three entries are identity because a
# world's class IS its name; Arcade is the exception that earns the mapping --
# it is the `:root` palette itself, so it is spelled as NO class at all, and
# an Arcade page renders the byte-identical `<html lang="en">` it always has.
ROOT_CLASSES = {ARCADE: "", MANOR: MANOR, HORROR: HORROR, CLEAN: CLEAN}


def root_class(name: str | None) -> str:
    """The root-element class for a world name; the default for anything else.

    `None` -- no parameter at all -- and an unrecognised name take the same
    path on purpose: both mean "this visitor has not told us a world we know",
    and the honest answer to both is the default one. Letting an unknown name
    through would put an undefined class on `<html>`, which is not an error
    anywhere; it is a page with no palette.

    Raising instead would be worse. The name arrives from a query parameter,
    so any visitor could 500 the site by typing one character. A dict lookup
    with a fallback makes the mapping itself the whitelist.
    """
    return ROOT_CLASSES.get(name, ROOT_CLASSES[DEFAULT_THEME])


def theme(request: HttpRequest) -> dict[str, object]:
    """Expose the active world, the vocabulary and the pin flag to every render.

    The single line in the codebase that knows where a world name comes from.
    Note what it does NOT do: supply `DEFAULT_THEME` as the `get` default. An
    absent parameter yields `None`, which misses `ROOT_CLASSES` and falls back
    inside `root_class` -- so "unknown becomes the default" is written once.
    Defaulting here as well would be a second copy of that rule, free to drift
    from the first the day either changes.

    The three keys are spelled literally in `base.html`, as a Django template
    must, so renaming one means editing that template in the same commit.
    """
    return {
        "theme_class": root_class(request.GET.get(THEME_PARAM)),
        # The whole vocabulary, handed to the client so the inline script never
        # spells a world name of its own. It needs BOTH halves of this mapping:
        # the keys are the whitelist it validates a stored value against, and
        # the values are what it puts on `<html>` -- including Arcade's empty
        # string, which no list of names could have carried. A second copy in
        # JavaScript would be free to drift from this one, and the symptom of
        # the drift would be a page with no palette rather than an error.
        "theme_worlds": ROOT_CLASSES,
        # Whether this render was pinned by the URL. The script restores a
        # stored world only when it was not, because `?theme=` is the QA
        # override: a tester who asks for one world must not be handed the
        # world they happen to have stored, and must not have their own
        # stored preference overwritten by looking at someone else's.
        "theme_pinned": THEME_PARAM in request.GET,
    }
