"""Read and write the verdict ledger from the command line.

This is how an agent writes back what a search concluded, and how you
inspect the ledger without opening the web app.

    python ledger.py stats
    python ledger.py list --status proposed
    python ledger.py propose Katsuobushi Maple_butter \
        --rationale "inosinate against caramel"
    python ledger.py reject Chocolate_cake Fish_paste --reason "no mechanism"
    python ledger.py vote Katsuobushi Maple_butter --up --actor tyler
    python ledger.py trial Katsuobushi Maple_butter --good --notes "on toast"
    python ledger.py log Katsuobushi Maple_butter
    python ledger.py export > verdicts.jsonl

Nothing here deletes or rewrites anything: a changed mind is a new
event, and ``log`` will show you both.
"""

import argparse
import json
import sys

from foodcombos.cli import use_utf8_stdout
from foodcombos.verdicts import DB_PATH, Ledger

STATUSES = ('proposed', 'rejected', 'tried_good', 'tried_bad', 'tried_mixed')


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--db', default=DB_PATH, help='ledger path')
    parser.add_argument('--json', action='store_true')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('stats', help='how much has been judged')

    listing = sub.add_parser('list', help='combinations and their verdicts')
    listing.add_argument('--status', action='append', choices=STATUSES,
                         default=[], help='repeatable')
    listing.add_argument('--order',
                         choices=('rating', 'score', 'recent', 'votes'),
                         default='rating')
    listing.add_argument('--tag', action='append', default=[],
                         help='facet:value, repeatable; all must match')
    listing.add_argument('-n', '--number', type=int, default=40)

    propose = sub.add_parser('propose', help='put a combination forward')
    propose.add_argument('foods', nargs='+')
    propose.add_argument('--actor', default='agent')
    propose.add_argument('--rationale', default='')
    propose.add_argument('--group', action='append', default=[],
                         help='source list per food, repeatable')

    reject = sub.add_parser('reject', help='rule one out without cooking it')
    reject.add_argument('foods', nargs='+')
    reject.add_argument('--actor', default='agent')
    reject.add_argument('--reason', default='')
    reject.add_argument('--group', action='append', default=[])

    vote = sub.add_parser('vote', help='upvote, downvote, or retract')
    vote.add_argument('foods', nargs='+')
    vote.add_argument('--actor', required=True)
    direction = vote.add_mutually_exclusive_group(required=True)
    direction.add_argument('--up', action='store_true')
    direction.add_argument('--down', action='store_true')
    direction.add_argument('--clear', action='store_true',
                           help='retract this actor\'s vote')

    trial = sub.add_parser('trial', help='record having actually eaten it')
    trial.add_argument('foods', nargs='+')
    trial.add_argument('--actor', default='tyler')
    trial.add_argument('--score', type=float, required=True,
                       help='how good was it, 0-100')
    trial.add_argument('--notes', default='')

    log = sub.add_parser('log', help='every event for one combination')
    log.add_argument('foods', nargs='+')

    sub.add_parser('export', help='the whole log as JSONL')

    sub.add_parser('tags', help='what tags exist and how common they are')
    sub.add_parser('tag', help='recompute tags from the scraped lists')

    sub.add_parser('init', help='create the ledger and exit')
    return parser.parse_args(argv)


def show_state(state, as_json):
    if as_json:
        print(json.dumps(state.__dict__, sort_keys=True, default=str))
        return
    bits = ['%-46s' % state.pretty(), '%-12s' % state.status]
    if state.n_trials:
        bits.append('%5.1f/100 (n=%d)' % (state.mean_score, state.n_trials))
    else:
        bits.append('%12s' % '-- untried')
    bits.append('%+d votes' % state.score)
    if state.rationale:
        bits.append('- %s' % state.rationale)
    print('  '.join(bits))


def main(argv=None):
    use_utf8_stdout()
    args = parse_args(argv)
    with Ledger.open(args.db) as ledger:
        if args.command == 'init':
            print('Ledger ready at %s (schema v%d)'
                  % (args.db, ledger.version()))

        elif args.command == 'stats':
            stats = ledger.stats()
            if args.json:
                print(json.dumps(stats, indent=2, sort_keys=True))
            else:
                print('combos   %d' % stats['combos'])
                print('events   %d' % stats['events'])
                print('actors   %s' % ', '.join(stats['actors']) or '(none)')
                for status, count in sorted(stats['by_status'].items()):
                    print('  %-12s %d' % (status, count))

        elif args.command == 'list':
            states = ledger.states(status=args.status or None,
                                   limit=args.number, order=args.order,
                                   tags=args.tag)
            for state in states:
                show_state(state, args.json)
            if not args.json:
                print('(%d combinations)' % len(states))

        elif args.command == 'propose':
            ledger.propose(args.foods, actor=args.actor, groups=args.group,
                           rationale=args.rationale)
            print('Proposed: %s' % ' + '.join(args.foods))

        elif args.command == 'reject':
            ledger.reject(args.foods, actor=args.actor, groups=args.group,
                          reason=args.reason)
            print('Rejected: %s' % ' + '.join(args.foods))

        elif args.command == 'vote':
            value = 1 if args.up else (-1 if args.down else 0)
            ledger.vote(args.foods, args.actor, value)
            print('Recorded vote %+d by %s' % (value, args.actor))

        elif args.command == 'trial':
            ledger.trial(args.foods, args.actor, args.score, notes=args.notes)
            state = ledger.state(args.foods)
            print('Recorded %g/100 by %s -> %s (mean %.1f over %d)'
                  % (args.score, args.actor, state.status,
                     state.mean_score, state.n_trials))

        elif args.command == 'log':
            for event in ledger.events(args.foods):
                print('%4d  %s  %-8s %-8s %s'
                      % (event['id'], event['ts'], event['kind'],
                         event['actor'], event['payload']))

        elif args.command == 'export':
            print(ledger.export_jsonl())

        elif args.command == 'tags':
            counts = ledger.tag_counts()
            if args.json:
                print(json.dumps(counts, indent=2, sort_keys=True))
            else:
                for facet, values in sorted(counts.items()):
                    print('%s' % facet)
                    for value, n in values:
                        print('  %-22s %d' % (value, n))

        elif args.command == 'tag':
            # Tags come from the scraped list pages, so the food database
            # has to be loaded to resolve combinations stored without
            # their source groups (anything proposed by hand in the app).
            from foodcombos.api import FoodDB
            try:
                food_db = FoodDB.load()
            except Exception:
                food_db = None
                print('No scraped database found; tagging only '
                      'combinations that already carry their groups.')
            tagged = ledger.retag(food_db)
            print('Tagged %d of %d combinations'
                  % (tagged, ledger.stats()['combos']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
