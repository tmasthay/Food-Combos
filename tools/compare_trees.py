"""Regression check for the scraper: is the new tree a superset of the old?

    python tools/compare_trees.py OLD_ROOT NEW_ROOT

Exits non-zero when the new tree lost a results file or a food that the
old tree had.  Extra findings in the new tree are reported and allowed --
that is the rule in CLAUDE.md.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foodcombos.cli import use_utf8_stdout  # noqa: E402
from foodcombos.paths import RESULTS_NAME, long_path  # noqa: E402


def collect(root):
    """``{relative_dir: [foods]}`` for every results file under ``root``."""
    table = {}
    for dirpath, _, filenames in os.walk(root):
        if RESULTS_NAME not in filenames:
            continue
        relative = os.path.relpath(dirpath, root).replace('\\', '/')
        path = long_path(os.path.join(dirpath, RESULTS_NAME))
        with open(path, encoding='utf-8') as handle:
            table[relative] = [line.strip() for line in handle if line.strip()]
    return table


def all_dirs(root):
    found = set()
    for dirpath, dirnames, _ in os.walk(root):
        for name in dirnames:
            found.add(
                os.path.relpath(os.path.join(dirpath, name), root)
                .replace('\\', '/')
            )
    return found


def by_page(table):
    """Re-key by page title, so a moved page is not read as a loss."""
    pages = {}
    for relative, foods in table.items():
        pages.setdefault(relative.rsplit('/', 1)[-1], set()).update(foods)
    return pages


def show(label, items, limit=12):
    items = sorted(items)
    print('  %s: %d' % (label, len(items)))
    for item in items[:limit]:
        print('      %s' % item)
    if len(items) > limit:
        print('      ... and %d more' % (len(items) - limit))


def main(old_root, new_root):
    use_utf8_stdout()
    old, new = collect(old_root), collect(new_root)
    old_dirs, new_dirs = all_dirs(old_root), all_dirs(new_root)

    print('=== directories ===')
    print('  old %d   new %d' % (len(old_dirs), len(new_dirs)))
    show('only in old', old_dirs - new_dirs)
    show('only in new', new_dirs - old_dirs)

    print('=== results files, by exact path ===')
    print('  old %d   new %d' % (len(old), len(new)))
    show('only in old', set(old) - set(new))
    show('only in new', set(new) - set(old))

    old_pages, new_pages = by_page(old), by_page(new)
    print('=== results files, by page title ===')
    print('  old %d   new %d' % (len(old_pages), len(new_pages)))
    lost_pages = set(old_pages) - set(new_pages)
    show('LOST pages', lost_pages)
    show('gained pages', set(new_pages) - set(old_pages))

    lost_foods = {}
    for page, foods in old_pages.items():
        gone = foods - new_pages.get(page, set())
        if gone:
            lost_foods[page] = gone

    print('=== foods ===')
    print('  old %d   new %d' % (
        sum(len(v) for v in old_pages.values()),
        sum(len(v) for v in new_pages.values()),
    ))
    if lost_foods:
        print('  LOST foods on %d pages' % len(lost_foods))
        for page, gone in sorted(lost_foods.items())[:10]:
            print('      %s: %s' % (page, sorted(gone)[:8]))

    ok = not lost_pages and not lost_foods
    print('\n%s' % ('PASS: new tree is a superset of old'
                    if ok else 'FAIL: new tree lost data'))
    return 0 if ok else 1


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
