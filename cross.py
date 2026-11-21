"""Cross several scraped lists into one output file.

    python cross.py --cartesian --out Queries/coffee_dessert \
        Final/Meals/Sweets/List_of_coffee_dishes/results.txt \
        Final/Meals/Sweets/List_of_desserts/results.txt

The legacy ``key=value`` spelling still works::

    python cross.py ext=txt cartesian=True out_file='Queries/coffee_dessert' \
        input_files='["a/results.txt","b/results.txt"]'
"""

import argparse
import ast
import sys

from foodcombos.cli import use_utf8_stdout
from foodcombos.combos import COLUMN_GAP, product_text
from foodcombos.paths import write_text

LEGACY_FLAGS = ('empty', 'cartesian', 'update')


def _rewrite_legacy_args(argv):
    """Translate ``key=value`` arguments into ordinary flags."""
    rewritten = []
    for arg in argv:
        if '=' not in arg:
            rewritten.append(arg)
            continue
        key, value = arg.split('=', 1)
        value = value.strip('\'"')
        if key == 'input_files':
            rewritten.extend(ast.literal_eval(value))
        elif key == 'out_file':
            rewritten.extend(['--out', value])
        elif key == 'ext':
            rewritten.extend(['--ext', value])
        elif key in LEGACY_FLAGS:
            if value[:1].lower() == 't':
                rewritten.append('--%s' % key)
        else:
            rewritten.append(arg)
    return rewritten


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('input_files', nargs='*', help='results.txt files to cross')
    parser.add_argument('--out', default='out', help='output file (default: %(default)s)')
    parser.add_argument('--ext', default='txt', help='extension for --out')
    parser.add_argument('--cartesian', action='store_true',
                        help='every combination instead of side-by-side columns')
    parser.add_argument('--empty', action='store_true',
                        help='keep blank lines from the inputs')
    parser.add_argument('--update', action='store_true',
                        help='re-scrape the database first')
    parser.add_argument('--gap', type=int, default=COLUMN_GAP)
    return parser.parse_args(_rewrite_legacy_args(
        sys.argv[1:] if argv is None else argv
    ))


def main(argv=None):
    use_utf8_stdout()
    args = parse_args(argv)
    if not args.input_files:
        raise SystemExit('No input files given. See --help.')

    out = args.out if args.out.endswith('.%s' % args.ext) \
        else '%s.%s' % (args.out, args.ext)

    if args.update:
        # Imported here, not at the top: crossing lists already on disk
        # is an offline operation and must not need the fetching stack.
        from foodcombos.scrape import run
        print('Refetching database...')
        run(refetch=True)

    text = product_text(
        args.input_files,
        keep_empty=args.empty,
        as_cartesian=args.cartesian,
        gap=args.gap,
    )
    write_text(out, text)
    print('Wrote %s' % out)


if __name__ == '__main__':
    main()
