"""Load the worked analysis in PLAUSIBLE_COMBOS.md into the ledger.

    python tools/seed_ledger.py            # writes to combos.db
    python tools/seed_ledger.py --db x.db

These are the agent's proposals and rejections from the first pass over
the scraped database, with the rationale and the narrowing that found
each one, so the web app opens with real material instead of an empty
list.  Re-running is harmless: the events are appended again but the
derived state is unchanged, because a second ``propose`` never overrides
the first.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foodcombos.cli import use_utf8_stdout  # noqa: E402
from foodcombos.verdicts import DB_PATH, Ledger  # noqa: E402

#: (foods, groups, rationale, narrowing-that-found-it)
PROPOSED = [
    (
        ['Arbroath_smokie', 'Rømmegrøt'],
        ['Meals.style.List_of_smoked_foods', 'Meals.Sweets.List_of_porridges'],
        'Hot-smoked haddock into sour-cream porridge: kedgeree logic with '
        'the rice swapped for a grain that brings its own acid.',
        {'slots': ['smoked', 'porridge'],
         'require_any': ['arbroath', 'rømmegrøt']},
    ),
    (
        ['Smoked_plum', 'Shrikhand'],
        ['Meals.style.List_of_smoked_foods',
         'Meals.seeds.List_of_yogurt-based_dishes_and_beverages'],
        'Saffron-cardamom strained yogurt lacks a bitter top note; smoked '
        'stone fruit supplies it. Risk is smoke swamping saffron.',
        {'slots': ['smoked', '*yogurt*'],
         'require_any': ['smoked plum', 'shrikhand']},
    ),
    (
        ['Katsuobushi', 'Maple_butter'],
        ['Meals.style.List_of_smoked_foods',
         'Meals.Sweets.List_of_foods_made_from_maple'],
        'Salt-plus-inosinate against caramel: bacon-and-maple with the fat '
        'removed and the smoke intensified. Best of the pass.',
        {'slots': ['smoked', 'maple'],
         'require_any': ['katsuobushi', 'maple butter']},
    ),
    (
        ['Marmite', 'Tsampa'],
        ['Meals.style.List_of_food_pastes', 'Meals.Sweets.List_of_porridges'],
        'Roasted barley and yeast extract share Maillard pyrazines, so the '
        'flavours run parallel; the extract supplies absent salt and '
        'glutamate. Use a quarter of what you think.',
        {'slots': ['*food_pastes*', 'porridge'],
         'require_any': ['marmite', 'tsampa']},
    ),
    (
        ['Doenjang', 'Sticky_toffee_pudding'],
        ['Meals.Asia.List_of_Korean_dishes',
         'Meals.origin.List_of_British_desserts'],
        'Date-and-treacle pudding is halfway to a savoury glaze; fermented '
        'soybean cuts it. Miso caramel is the precedent. Riskiest here.',
        {'slots': ['*korean*', '*british_desserts*'],
         'require_any': ['doenjang', 'sticky toffee']},
    ),
    (
        ['Pickled_walnuts', 'Blue_Stilton'],
        ['Meals.style.List_of_pickled_foods',
         'Meals.origin.List_of_English_cheeses'],
        'Control, not discovery: a real British pairing the method found '
        'from two unrelated lists. Tannic sour-sweet against blue fat.',
        {'slots': ['pickled', '*english_cheeses*'],
         'require_any': ['pickled walnut', 'stilton']},
    ),
    (
        ['Umeboshi', 'Kaya_toast'],
        ['Meals.style.List_of_pickled_foods', 'Meals.seeds.List_of_toast_dishes'],
        'Kaya toast already comes with a savoury counterweight; umeboshi '
        'does that job with acid instead of salt alone.',
        {'slots': ['pickled', 'toast'],
         'require_any': ['umeboshi', 'kaya']},
    ),
    (
        ['Beni_shōga', 'Porchetta'],
        ['Meals.style.List_of_pickled_foods', 'Meals.seeds.List_of_pork_dishes'],
        'Porchetta wants a sharp pickle; ginger in umezu brings acid plus a '
        'warm aromatic that sits on fennel rather than fighting it.',
        {'slots': ['pickled', '*pork*'],
         'require_any': ['beni', 'porchetta']},
    ),
    (
        ['Harissa', 'Welsh_rarebit'],
        ['Meals.Related.List_of_condiments', 'Meals.seeds.List_of_toast_dishes'],
        'Rarebit is built on heat and funk; harissa substitutes for the '
        'mustard with capsaicin and caraway, and the caraway finds the beer.',
        {'slots': ['*condiments*', 'toast'],
         'require_any': ['harissa', 'welsh rarebit']},
    ),
    (
        ['Ricotta', 'Vincotto'],
        ['Meals.style.List_of_smoked_foods', 'Meals.Sweets.List_of_syrups'],
        'Smoked ricotta is drier and saltier than fresh, so it needs a syrup '
        'with acid rather than honey. Both southern Italian.',
        {'slots': ['smoked', '*syrups*'],
         'require_any': ['ricotta', 'vincotto']},
    ),
    (
        ['Maple_butter', 'Oatcake'],
        ['Meals.Sweets.List_of_foods_made_from_maple',
         'Meals.seeds.List_of_crackers'],
        'Oatcakes exist to carry fat; maple butter is fat-free sugar that '
        'behaves like fat. Oat and maple share a toasted-grain register.',
        {'slots': ['*maple*', '*crackers*'],
         'require_any': ['maple butter', 'oatcake']},
    ),
    (
        ['Birch_syrup', 'Lox'],
        ['Meals.Sweets.List_of_syrups', 'Meals.style.List_of_smoked_foods'],
        'Birch is savoury and mineral, not maple; used in Alaska and Finland '
        'to glaze fish. A brushing, not a pour -- lox is already salty.',
        {'slots': ['*syrups*', 'smoked'],
         'require_any': ['birch syrup', 'lox']},
    ),
    (
        ['Tahini', 'Warabimochi'],
        ['Meals.style.List_of_food_pastes',
         'Meals.origin.List_of_Japanese_desserts_and_sweets'],
        'Kinako and tahini share a roasted-seed register, but tahini brings '
        'fat and bitterness the flour cannot. Halva, made with mochi.',
        {'slots': ['*food_pastes*', '*japanese_desserts*'],
         'require_any': ['tahini', 'warabimochi']},
    ),
]

#: Rejections from the same pass, with why.  These are the ones the
#: search should stop re-offering.
REJECTED = [
    (['Chocolate-covered_prune', 'Chocolate_truffle'],
     'The same idea twice -- what distinct_groups and the shared-token '
     'penalty exist to suppress.'),
    (['Pickled_cucumber', 'Corned_beef'],
     'Already a sandwich.'),
    (['Espresso_rub', 'Pork_ribs'],
     'Already on List_of_coffee_dishes; the database contains the answer, '
     'so it is not a discovery.'),
    (['Peanut_paste', 'Brazil'],
     'List_of_doughnut_varieties has a country column and the scraper '
     'cannot tell a country from a doughnut. Noise, not a combination.'),
    (['Paprika', 'Tsampa'],
     'Plausible-sounding and empty: paprika is an ingredient, not a thing '
     'you combine with a porridge.'),
    (['Apple', 'Avocado_toast'],
     '"Apple" is the fruit article, present because pickled apple exists. '
     'Single-word generic entries are too vague to judge.'),
]


def main(argv=None):
    use_utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--db', default=DB_PATH)
    parser.add_argument('--actor', default='agent')
    args = parser.parse_args(argv)

    with Ledger.open(args.db) as ledger:
        for foods, groups, rationale, narrowing in PROPOSED:
            ledger.propose(foods, actor=args.actor, groups=groups,
                           rationale=rationale, narrowing=narrowing)
        for foods, reason in REJECTED:
            ledger.reject(foods, actor=args.actor, reason=reason)
        stats = ledger.stats()

    print('Seeded %d proposals and %d rejections into %s'
          % (len(PROPOSED), len(REJECTED), args.db))
    print('Ledger now holds %d combinations, %d events'
          % (stats['combos'], stats['events']))
    for status, count in sorted(stats['by_status'].items()):
        print('  %-12s %d' % (status, count))
    return 0


if __name__ == '__main__':
    sys.exit(main())
