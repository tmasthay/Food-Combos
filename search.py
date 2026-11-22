"""Narrowed search over the scraped food database.

    python search.py summary
    python search.py groups coffee dessert
    python search.py foods mango
    python search.py combos --slot coffee --slot dessert -n 10
    python search.py combos --spec narrowing.yaml

``--slot`` is the workhorse: one per element of the combination, each a
pattern matched against list-page names.  See ``CLAUDE.md`` for the full
vocabulary of a narrowing.
"""

import argparse
import json

from foodcombos.api import FoodDB, Narrowing, shared_token_penalty
from foodcombos.cli import use_utf8_stdout


def build_narrowing(args):
    if args.spec:
        narrowing = Narrowing.from_yaml(args.spec)
    else:
        narrowing = Narrowing()
    overrides = {}
    if args.slot:
        overrides['slots'] = args.slot
    if args.arity is not None:
        overrides['arity'] = args.arity
    if args.include:
        overrides['include'] = args.include
    if args.exclude:
        overrides['exclude'] = args.exclude
    if args.exclude_food:
        overrides['exclude_foods'] = args.exclude_food
    if args.require_any:
        overrides['require_any'] = args.require_any
    if args.number is not None:
        overrides['limit'] = args.number
    if args.per_group is not None:
        overrides['per_group'] = args.per_group
    if args.seed is not None:
        overrides['seed'] = args.seed
    if args.allow_same_group:
        overrides['distinct_groups'] = False
    if args.raw:
        overrides['drop_noise'] = False
    if args.include_settled:
        overrides['exclude_settled'] = False
    if args.only_new:
        overrides['exclude_known'] = True
    if args.only_status:
        overrides['only_status'] = args.only_status
        overrides['exclude_settled'] = False
    return narrowing.with_(**overrides)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--data', default='data.yaml', help='database to load')
    parser.add_argument('--root', default='Final', help='fallback scraped tree')
    parser.add_argument('--ledger', default='combos.db',
                        help='verdict database; ignored if absent')
    parser.add_argument('--json', action='store_true', help='machine-readable output')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('summary', help='how big the database is')

    groups = sub.add_parser('groups', help='find list pages by name')
    groups.add_argument('patterns', nargs='*')

    foods = sub.add_parser('foods', help='find individual foods by name')
    foods.add_argument('patterns', nargs='+')

    show = sub.add_parser('show', help='print one list page')
    show.add_argument('group')
    show.add_argument('--raw', action='store_true',
                      help='include scraped noise (interlanguage/red links)')

    biggest = sub.add_parser('largest', help='the fattest list pages')
    biggest.add_argument('-n', '--number', type=int, default=20)

    combos = sub.add_parser('combos', help='sample combinations')
    combos.add_argument('--spec', help='narrowing written as YAML')
    combos.add_argument('--slot', action='append', default=[],
                        help='group pattern for one element (repeatable)')
    combos.add_argument('--arity', type=int, help='elements per combination')
    combos.add_argument('--include', action='append', default=[])
    combos.add_argument('--exclude', action='append', default=[])
    combos.add_argument('--exclude-food', action='append', default=[])
    combos.add_argument('--require-any', action='append', default=[])
    combos.add_argument('-n', '--number', type=int, help='how many to return')
    combos.add_argument('--per-group', type=int)
    combos.add_argument('--seed', type=int)
    combos.add_argument('--allow-same-group', action='store_true')
    combos.add_argument('--raw', action='store_true',
                        help='do not hide scraped non-food entries')
    combos.add_argument('--include-settled', action='store_true',
                        help='keep combinations already rejected or disliked')
    combos.add_argument('--only-new', action='store_true',
                        help='only combinations the ledger has never seen')
    combos.add_argument('--only-status', action='append', default=[],
                        choices=('proposed', 'rejected', 'tried_good',
                                 'tried_bad', 'tried_mixed'),
                        help='review past verdicts instead of finding new ones')
    combos.add_argument('--rank-distinct', action='store_true',
                        help='rank by the built-in shared-token penalty')
    combos.add_argument('--urls', action='store_true', help='print wiki links')
    return parser.parse_args(argv)


def main(argv=None):
    use_utf8_stdout()
    args = parse_args(argv)
    db = FoodDB.load(path=args.data, root=args.root, ledger=args.ledger)

    if args.command == 'summary':
        summary = db.summary()
        print(json.dumps(summary, indent=2) if args.json else
              '\n'.join('%-14s %s' % (k, v) for k, v in summary.items()))

    elif args.command == 'groups':
        names = db.search_groups(*args.patterns)
        if args.json:
            print(json.dumps(names, indent=2))
        else:
            for name in names:
                print('%-70s %d' % (name, len(db.groups[name])))
            print('(%d groups)' % len(names))

    elif args.command == 'foods':
        hits = db.search_foods(*args.patterns)
        if args.json:
            print(json.dumps(hits, indent=2))
        else:
            for group, food in hits:
                print('%-40s %s' % (food, group))
            print('(%d foods)' % len(hits))

    elif args.command == 'show':
        for food in db.group(args.group, drop_noise=not args.raw):
            print(food)

    elif args.command == 'largest':
        for name, size in db.largest_groups(args.number):
            print('%-70s %d' % (name, size))

    elif args.command == 'combos':
        narrowing = build_narrowing(args)
        score = shared_token_penalty if args.rank_distinct else None
        results = db.narrow(narrowing, score=score)
        if args.json:
            print(json.dumps([
                {'foods': list(c.foods), 'groups': list(c.groups),
                 'urls': list(c.urls())}
                for c in results
            ], indent=2))
        else:
            for combo in results:
                print(combo.labelled())
                if args.urls:
                    for url in combo.urls():
                        print('    %s' % url)
            suffix = ''
            if db.judged:
                suffix = '; %d judged combinations known' % len(db.judged)
            print('(%d combinations; seed %s%s)'
                  % (len(results), narrowing.seed, suffix))


if __name__ == '__main__':
    main()
