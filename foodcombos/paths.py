"""Filesystem helpers for the scraped ``Final/`` tree.

Wikipedia page titles become directory names, and they are hostile to
filesystems: they carry quotes, ampersands, colons and slashes, and the
nesting they produce runs past Windows' 260-character path limit.  Every
read and write in this package goes through here so those two problems
are solved exactly once.
"""

import os

# Stripped from path components.  The first group is what the original
# scraper removed; the second is what Windows additionally forbids.
FORBIDDEN_CHARS = '\'()&\\' + ':*?"<>|'

DATA_ROOT = 'Final'
RESULTS_NAME = 'results.txt'


def sanitize(rel_path):
    """Strip filesystem-hostile characters from a ``/``-separated path.

    ``/`` is intentionally preserved: a page title such as
    ``Wikipedia:WikiProject_Food_and_drink/Beverages_Task_Force`` is
    allowed to nest, which is how the original scraper behaved.
    """
    for bad in FORBIDDEN_CHARS:
        rel_path = rel_path.replace(bad, '')
    return rel_path


def long_path(path):
    """Return ``path`` in a form the OS will accept.

    On Windows the ``\\\\?\\`` prefix lifts the 260-character ``MAX_PATH``
    limit, which the deeper corners of the scraped tree exceed.  On other
    platforms this is the identity.
    """
    if os.name != 'nt':
        return path
    path = os.path.abspath(path)
    return path if path.startswith('\\\\?\\') else '\\\\?\\' + path


def resolve(rel_path, root=None):
    """Sanitize ``rel_path`` and anchor it under ``root`` (default: cwd)."""
    root = (root or os.getcwd()).replace('\\', '/')
    if os.path.isabs(rel_path):
        rel_path = os.path.relpath(rel_path, root).replace('\\', '/')
    return '%s/%s' % (root, sanitize(rel_path))


def write_text(rel_path, text, root=None):
    """Write ``text`` to ``rel_path``, creating parent directories.

    Returns the full path actually written.
    """
    dest = resolve(rel_path, root=root)
    os.makedirs(long_path(os.path.dirname(dest)), exist_ok=True)
    with open(long_path(dest), 'w', encoding='utf-8') as handle:
        handle.write(text)
    return dest


def read_text(path):
    with open(long_path(path), 'r', encoding='utf-8') as handle:
        return handle.read()


def exists(path):
    return os.path.exists(long_path(path))


def iter_dirs(root=DATA_ROOT):
    """Every directory under ``root``, sorted, with ``/`` separators."""
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        for name in dirnames:
            found.append(('%s/%s' % (dirpath, name)).replace('\\', '/'))
    return sorted(found)


def iter_list_dirs(root=DATA_ROOT):
    """Directories that correspond to a Wikipedia ``List_of_*`` page."""
    return [d for d in iter_dirs(root) if d.rsplit('/', 1)[-1].startswith('List')]
