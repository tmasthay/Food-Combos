"""Turn ``Portal:Food`` into the ``Final/`` directory tree.

The portal page carries two navboxes -- ``Template:Cuisines`` and
``Template:Meals_navbox`` -- and the tree mirrors their shape::

    Final/<navbox>/<row label>/<page title>/

Each level is produced the same way: find every occurrence of a marker
regex, and hand the text between consecutive markers to the next level
down.  ``split_sections`` is that single operation, used three times.
"""

import re

from .fetch import fetch_markdown, page_url
from .paths import DATA_ROOT, write_text

#: The "v" (view) link that opens each navbox.  Wikipedia serves these
#: hrefs absolute today and served them relative in the past, so both
#: spellings are accepted.
NAVBOX_RE = re.compile(
    r'\[v\]\((?:https?://en\.wikipedia\.org)?/wiki/'
    r'Template:(?P<template>Cuisines|Meals_navbox) '
    r'"Template:(?:Cuisines|Meals navbox)"\)'
)

#: A navbox row label, e.g. the ``Continental|`` that heads a table row.
ROW_LABEL_RE = re.compile(r'(?P<label>\w+)\|')

#: A two-space-indented bullet holding a link to an article.
PAGE_LINK_RE = re.compile(r'\n  \* \[.*\].*/wiki/.* ".*".*')

PORTAL_URL = page_url('Portal:Food')


def navbox_name(match):
    """``Template:Meals_navbox`` -> ``Meals``."""
    return match.group('template').split('_')[0]


def row_label(match):
    return match.group('label')


def page_title(match):
    """Pull the article title out of a markdown bullet link."""
    return match.group(0).replace('\n', '').split('/wiki/')[1].split(' ')[0]


def split_sections(text, pattern, name_of):
    """Split ``text`` on ``pattern`` into ``[(name, body), ...]``.

    ``body`` runs from the end of one marker to the start of the next;
    anything before the first marker is preamble and is discarded.
    """
    matches = list(pattern.finditer(text))
    sections = []
    for index, match in enumerate(matches):
        stop = (
            matches[index + 1].start()
            if index + 1 < len(matches)
            else len(text)
        )
        sections.append((name_of(match), text[match.end():stop]))
    return sections


#: The tree, outermost first: (marker regex, name extractor).
LAYERS = (
    (NAVBOX_RE, navbox_name),
    (ROW_LABEL_RE, row_label),
    (PAGE_LINK_RE, page_title),
)


def _eat_layers(text, parent, layers, leaves):
    """Recursively carve ``text`` into directories, collecting leaf dirs."""
    if not layers:
        leaves.append(parent)
        return
    (pattern, name_of), rest = layers[0], layers[1:]
    for name, body in split_sections(text, pattern, name_of):
        child = '%s/%s' % (parent, name)
        write_text('%s/%s_total.txt' % (child, name), body)
        _eat_layers(body, child, rest, leaves)


def build_tree(markdown, root=DATA_ROOT):
    """Write the directory tree for ``markdown``; return the leaf dirs."""
    leaves = []
    _eat_layers(markdown, root, LAYERS, leaves)
    return leaves


def scrape_portal(root=DATA_ROOT):
    """Fetch ``Portal:Food``, archive it, and build the tree beneath it."""
    raw, markdown = fetch_markdown(PORTAL_URL)
    write_text('%s/wiki_portal_raw_html.txt' % root, raw)
    write_text('%s/wiki_portal_cleaned.txt' % root, markdown)
    return build_tree(markdown, root=root)
