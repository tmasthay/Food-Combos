"""Wikipedia naming: titles in, URLs out.  No network, no dependencies.

This is split out from :mod:`foodcombos.fetch` on purpose.  Search works
entirely offline against the already-scraped database, and the only thing
it wants from the Wikipedia side is a link it can print.  Keeping that in
its own stdlib-only module means ``search.py`` never imports the
fetching stack at all.
"""

import urllib.parse

WIKI_BASE = 'https://en.wikipedia.org/wiki/'

#: Characters left alone when percent-encoding a title.  ``#`` stays so
#: that a title such as ``Mustard_condiment#American`` keeps behaving as
#: a fragment, i.e. resolves to the base article.
URL_SAFE = "/:#?&=,()'!*+$;@~"


def page_url(title):
    """Wikipedia URL for ``title``, safe for non-ASCII titles."""
    return WIKI_BASE + urllib.parse.quote(title, safe=URL_SAFE)
