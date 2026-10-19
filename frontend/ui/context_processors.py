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
the codebase that knows a world name arrives as a query parameter. US-5.3
replaces the source with a stored preference by rewriting that one line, and
every rule about what a name resolves to stays put.
"""

from django.http import HttpRequest

# The query parameter is this story's only source of a world name. Persistence
# and the chooser are US-5.3 to US-5.6; until they land this is both how a
# theme is selected and how the by-hand 320px check reaches all four worlds,
# and it stays afterwards as the QA override that needs no stored state.
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


def theme(request: HttpRequest) -> dict[str, str]:
    """Expose the active world's root class to every template render.

    The single line in the codebase that knows where a world name comes from.
    Note what it does NOT do: supply `DEFAULT_THEME` as the `get` default. An
    absent parameter yields `None`, which misses `ROOT_CLASSES` and falls back
    inside `root_class` -- so "unknown becomes the default" is written once.
    Defaulting here as well would be a second copy of that rule, free to drift
    from the first the day either changes.
    """
    # `base.html` spells `theme_class` literally, as a Django template must,
    # so renaming this key means editing that template in the same commit.
    return {"theme_class": root_class(request.GET.get(THEME_PARAM))}
