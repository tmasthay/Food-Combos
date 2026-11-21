"""Turn scraped list-page names into tags you can filter and rank by.

A combination is interesting along axes the raw scrape does not name:
"one side is Italian", "one side is a pasta", "one side was smoked".
Those are all recoverable from the list page a food came from --
``Meals.Europe.List_of_Italian_foods_and_drinks`` says *Italian*, and
``Meals.seeds.List_of_pasta`` says *pasta* -- so the tags are derived,
not typed in by hand.

Four facets, because they answer different questions:

``cuisine``    where it is from (italian, japanese, korean, ...)
``course``     what role it plays at the table (dessert, soup, bread, ...)
``technique``  what was done to it (smoked, pickled, fermented, ...)
``ingredient`` what it is made of (pasta, beef, coconut, maple, ...)

Tags are derived data, like the SQL views: they are rebuilt wholesale by
``ledger.py tag`` rather than migrated, so changing a rule below costs a
re-run and nothing else.
"""

import re

#: Cuisines, matched as the leading adjective of a list-page name.
#: ``Greek_Protected_Designations_of_Origin_cheeses`` is why this matches
#: a prefix rather than requiring the whole name.
CUISINES = (
    'American', 'Armenian', 'Asian', 'Australian', 'Azerbaijani',
    'Brazilian', 'British', 'Chinese', 'Dutch', 'Ecuadorian', 'English',
    'Ethiopian', 'European', 'French', 'German', 'Greek', 'Indian',
    'Indonesian', 'Irish', 'Israeli', 'Italian', 'Jamaican', 'Japanese',
    'Korean', 'Maltese', 'Mexican', 'Moroccan', 'Nepalese', 'Norwegian',
    'Pakistani', 'Palestinian', 'Peruvian', 'Philippine', 'Polish',
    'Portuguese', 'Russian', 'Singaporean', 'Spanish', 'Swiss', 'Syrian',
    'Sámi', 'Taiwanese', 'Thai', 'Uzbek', 'Vietnamese', 'Welsh',
)

#: Extra cuisine spellings that are not a leading adjective.
CUISINE_PHRASES = {
    'cuisines_of_the_Americas': 'american',
    'dishes_from_the_Caucasus': 'caucasian',
    'New_Zealand': 'australian',
    'Eritrean': 'ethiopian',
}

#: What role the food plays. Order matters: the first match wins, so the
#: more specific entries come first ("cheese_soups" is a soup, not a
#: cheese; "breakfast_cereals" is breakfast, not a cereal grain).
COURSES = (
    ('dessert', ('dessert', 'sweets', 'cake', 'cookie', 'pastry',
                 'doughnut', 'chocolate-covered')),
    ('soup', ('soup', 'stew', 'chowder')),
    ('bread', ('bread', 'toast', 'pancake', 'tortilla', 'fried_dough')),
    ('cheese', ('cheese',)),
    ('condiment', ('condiment', 'sauce', 'chutney', 'mayonnaise',
                   'mustard', 'syrup', 'spread', 'paste', 'relish')),
    ('snack', ('snack', 'cracker', 'crisps')),
    ('breakfast', ('breakfast', 'brunch', 'porridge', 'cereal')),
    ('salad', ('salad',)),
    ('sandwich', ('sandwich', 'hot_dog', 'kebab')),
    ('drink', ('drink', 'beverage', 'cocktail', 'coffee')),
    ('seasoning', ('herbs_and_spices', 'food_additives', 'vegetable_oils',
                   'edible_seeds')),
)

#: What was done to it.
TECHNIQUES = (
    'smoked', 'pickled', 'fermented', 'dried', 'deep_fried', 'steamed',
    'spit-roasted', 'stuffed', 'rolled', 'instant', 'baked', 'barbecue',
    'cured',
)

#: What it is made of.  Keyed by the word as it appears in a page name.
INGREDIENTS = (
    'almond', 'apple', 'avocado', 'banana', 'bean', 'beef', 'broccoli',
    'buckwheat', 'butter', 'cabbage', 'carrot', 'cherry', 'chicken',
    'clam', 'coconut', 'crab', 'dumpling', 'egg', 'eggplant', 'garlic',
    'goat', 'grape', 'lamb', 'legume', 'lemon', 'maize', 'mango',
    'maple', 'meatball', 'melon', 'mushroom', 'noodle', 'onion', 'pasta',
    'plum', 'pork', 'rice', 'sausage', 'seafood', 'sesame', 'shrimp',
    'soy', 'squash', 'pumpkin', 'sweet_potato', 'tofu', 'tomato', 'tuna',
    'yogurt', 'fish', 'vegetable', 'fruit',
)

FACETS = ('cuisine', 'course', 'technique', 'ingredient')


def page_name(group):
    """``Meals.Sweets.List_of_cakes`` -> ``cakes``."""
    leaf = group.rsplit('.', 1)[-1]
    return re.sub(r'^List_of_', '', leaf)


def _has(name, needle):
    """Word-ish containment, so 'bean' does not match 'Caribbean'."""
    return re.search(r'(^|[_\-,])%s' % re.escape(needle), name) is not None


def tags_for_group(group):
    """Every tag implied by one list page, as ``facet:value`` strings."""
    name = page_name(group)
    lowered = name.lower()
    found = set()

    for phrase, value in CUISINE_PHRASES.items():
        if phrase.lower() in lowered:
            found.add('cuisine:%s' % value)
    for cuisine in CUISINES:
        if lowered.startswith(cuisine.lower()):
            found.add('cuisine:%s' % cuisine.lower())
            break

    for course, needles in COURSES:
        if any(n in lowered for n in needles):
            found.add('course:%s' % course)
            break

    for technique in TECHNIQUES:
        if _has(lowered, technique):
            found.add('technique:%s' % technique)

    for ingredient in INGREDIENTS:
        if _has(lowered, ingredient):
            found.add('ingredient:%s' % ingredient)

    return found


def tags_for_combo(groups):
    """Tags for a whole combination: the union over its members' pages."""
    found = set()
    for group in groups or ():
        if group:
            found |= tags_for_group(group)
    return found


def groups_for_food(food_db, food):
    """Which list pages a food appears on, for combos stored without them."""
    return [
        group
        for group, foods in food_db.groups.items()
        if food in foods
    ]


def resolve_groups(food_db, foods, groups):
    """Fill in missing groups by looking foods up in the scrape.

    The web app lets a human propose a combination by typing two names,
    so it has no idea which list pages they came from.  The scrape does.
    """
    groups = list(groups or [])
    resolved = []
    for index, food in enumerate(foods):
        stored = groups[index] if index < len(groups) else None
        if stored:
            resolved.append(stored)
        elif food_db is not None:
            resolved.extend(groups_for_food(food_db, food))
    return resolved


def split(tag):
    """``cuisine:italian`` -> ``('cuisine', 'italian')``."""
    facet, _, value = tag.partition(':')
    return facet, value
