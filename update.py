"""Build the food database by scraping Wikipedia.

    python update.py --fetch      # walk the portal and download the pages
    python update.py              # re-parse pages already on disk

The legacy ``key=value`` spelling still works::

    python update.py fetch=True
"""

import argparse
import sys

from foodcombos.cli import use_utf8_stdout
from foodcombos.lists import MIN_RESULTS
from foodcombos.paths import DATA_ROOT
from foodcombos.scrape import run


def _rewrite_legacy_args(argv):
    """Accept the old ``fetch=True`` form alongside ``--fetch``."""
    rewritten = []
    for arg in argv:
        if arg.lower().startswith('fetch='):
            if arg.split('=', 1)[1][:1].lower() == 't':
                rewritten.append('--fetch')
        else:
            rewritten.append(arg)
    return rewritten


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--fetch', action='store_true',
        help='download Portal:Food and every page it links (slow, cached)',
    )
    parser.add_argument(
        '--root', default=DATA_ROOT,
        help='directory tree to build (default: %(default)s)',
    )
    parser.add_argument(
        '--min-results', type=int, default=MIN_RESULTS,
        help='drop pages yielding fewer foods (default: %(default)s)',
    )
    parser.add_argument('-q', '--quiet', action='store_true')
    return parser.parse_args(_rewrite_legacy_args(
        sys.argv[1:] if argv is None else argv
    ))


def main(argv=None):
    use_utf8_stdout()
    args = parse_args(argv)
    run(
        refetch=args.fetch,
        root=args.root,
        min_results=args.min_results,
        verbose=not args.quiet,
    )


if __name__ == '__main__':
    main()
