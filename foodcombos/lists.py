"""Turn a fetched ``List_of_*`` page into a list of food names."""

import re

from .paths import RESULTS_NAME, read_text, write_text

#: Substrings that disqualify an entry (case-insensitive).  These knock
#: out navigation, meta-articles and drinks, leaving edible nouns.
EXCLUSIONS = (
    'cuisine', 'list', 'beer',
    ':', '#', 'dish',
    'food', 'meal', 'product',
    'festival', 'page', 'history',
    'wine', 'cocktail',
)

#: Everything after "See also" is navigation, not food.
SEE_ALSO_RE = re.compile(r'#[#]*[ \n]*See[ \n]*also')

#: A bullet chunk whose first non-blank line links to an article.
LINKED_ITEM_RE = re.compile(r'[ \n\t_]*.*/wiki/.* ".*".*')

#: Pages yielding fewer than this many foods are treated as noise and
#: produce no ``results.txt`` -- they are usually prose articles or
#: tables that happen to be named ``List_of_*``.
MIN_RESULTS = 5


def is_excluded(name):
    lowered = name.lower()
    return any(bad.lower() in lowered for bad in EXCLUSIONS)


def extract_foods(markdown):
    """Return the article titles bulleted in ``markdown`` before "See also"."""
    body = SEE_ALSO_RE.split(markdown)[0]
    titles = [
        chunk.split('/wiki/')[1].split(' ')[0]
        for chunk in body.split('*')
        if LINKED_ITEM_RE.match(chunk)
    ]
    return [t for t in titles if t and not is_excluded(t)]


def clean_page_path(page_dir):
    """Where ``fetch`` stashed the html2text rendering of ``page_dir``."""
    title = page_dir.rsplit('/', 1)[-1]
    return '%s/WebContentClean_%s.txt' % (page_dir, title)


def process_page(page_dir, min_results=MIN_RESULTS):
    """Write ``results.txt`` for ``page_dir``; return the foods found.

    Returns ``None`` when the page could not be read at all.
    """
    try:
        markdown = read_text(clean_page_path(page_dir))
    except OSError:
        return None
    foods = extract_foods(markdown)
    if len(foods) >= min_results:
        write_text('%s/%s' % (page_dir, RESULTS_NAME), '\n'.join(foods))
    return foods
