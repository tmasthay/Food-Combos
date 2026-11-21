"""Human-guided narrowed search over the scraped food database.

The database is a few hundred lists holding a few ten-thousand foods;
the cartesian product of any two of them is already too large to read.
The point of this module is to let a *human* hand an *agent* a small,
declarative description of where to look -- a :class:`Narrowing` -- and
get back a short, labelled list of candidate combinations that the agent
can then judge for plausibility.

A narrowing is deliberately coarse.  It says things like "one thing from
a coffee list, one thing from a dessert list, nothing with 'sauce' in the
name, twenty of them, seed 7".  It does not try to model taste.

    >>> db = FoodDB.load()
    >>> db.search_groups('coffee')
    ['Meals.Sweets.List_of_coffee_dishes', ...]
    >>> narrowing = Narrowing(slots=['*coffee*', '*dessert*'], limit=5, seed=7)
    >>> for combo in db.narrow(narrowing):
    ...     print(combo.pretty())

See ``CLAUDE.md`` for how to read a narrowing somebody else wrote.
"""

import fnmatch
import itertools
import os
import random
from dataclasses import dataclass, field, replace

from . import database
from .wiki import page_url

WILDCARDS = '*?['

#: Products up to this many combinations are enumerated exactly; larger
#: ones are sampled.  Enumeration is what makes a pinned search ("that
#: cheese with that chutney") reliably findable.
ENUMERATE_CAP = 300000


def _as_pattern(text):
    """Treat a bare word as a substring match, anything else as a glob."""
    lowered = text.lower()
    if any(char in lowered for char in WILDCARDS):
        return lowered
    return '*%s*' % lowered


def _product_size(pools):
    total = 1
    for pool in pools:
        total *= len(pool)
    return total


def matches_any(name, patterns):
    """Glob-match ``name`` against ``patterns``, ignoring case and ``_``.

    A human types "maple butter"; the database says ``Maple_butter``.
    Both spellings are tried so neither side has to care.
    """
    forms = {name.lower(), name.lower().replace('_', ' ')}
    return any(
        fnmatch.fnmatch(form, _as_pattern(p.replace('_', ' ')))
        or fnmatch.fnmatch(form, _as_pattern(p))
        for p in patterns
        for form in forms
    )


def contains(name, needle):
    """Substring test that also ignores case and ``_`` vs space."""
    hay = name.lower().replace('_', ' ')
    return needle.lower().replace('_', ' ') in hay


def unescape(food):
    r"""Drop html2text's markdown escapes: ``Amba_\(condiment\)``."""
    return food.replace('\\', '')


def pretty_food(food):
    """``Angel_food_cake`` -> ``Angel food cake``."""
    return unescape(food).replace('_', ' ')


def is_noise(food):
    """True for scraped titles that are not food names at all.

    Wikipedia's list pages carry interlanguage links (percent-encoded
    titles), red links (``?action=edit&redlink=1``) and the odd stray
    anchor.  They are kept in ``Final/`` -- the scrape is a record of
    what the page said -- but there is no reason to show them to a human
    hunting for combinations.
    """
    return (
        '%' in food
        or '?' in food
        or not food[:1].isascii()
    )


@dataclass(frozen=True)
class Combo:
    """One candidate combination, with provenance."""

    items: tuple  # ((group, food), ...)

    @property
    def foods(self):
        return tuple(food for _, food in self.items)

    @property
    def groups(self):
        return tuple(group for group, _ in self.items)

    def urls(self):
        return tuple(page_url(unescape(food)) for _, food in self.items)

    def pretty(self):
        return ' + '.join(pretty_food(food) for food in self.foods)

    def labelled(self):
        return ' + '.join(
            '%s [%s]' % (pretty_food(food), group.rsplit('.', 1)[-1])
            for group, food in self.items
        )


@dataclass
class Narrowing:
    """A human's description of where an agent should look.

    ``slots``
        One pattern per element of the combination, e.g.
        ``['*coffee*', '*dessert*']`` asks for pairs drawn from a coffee
        list and a dessert list.  Patterns are matched against group
        names (``Meals.Sweets.List_of_cakes``); a bare word such as
        ``coffee`` means "contains coffee".
    ``arity``
        Used instead of ``slots`` when every element may come from the
        same pool: ``include`` selects the pool, ``arity`` its size.
    ``include`` / ``exclude``
        Group patterns defining the pool for ``arity`` searches, and
        filters applied on top of ``slots``.
    ``include_foods`` / ``exclude_foods``
        Patterns applied to individual food names.
    ``require_any`` / ``require_all``
        Substrings at least one / every food in a combination must have.
    ``distinct_groups``
        Forbid two elements of one combination coming from the same list.
    ``drop_noise``
        Skip scraped entries that are not food names (see :func:`is_noise`).
        On by default; turn it off to see the raw scrape.
    ``limit``
        How many combinations to return.  ``None`` means "all of them",
        which is usually a mistake.
    ``per_group``
        Cap on foods taken from any single list, to keep huge lists from
        swamping small ones.
    ``seed``
        Sampling seed, so a narrowing is reproducible and an agent can
        quote it back.
    """

    slots: list = field(default_factory=list)
    arity: int = 2
    include: list = field(default_factory=list)
    exclude: list = field(default_factory=list)
    include_foods: list = field(default_factory=list)
    exclude_foods: list = field(default_factory=list)
    require_any: list = field(default_factory=list)
    require_all: list = field(default_factory=list)
    distinct_groups: bool = True
    drop_noise: bool = True
    limit: int = 20
    per_group: int = 0
    seed: int = 0
    note: str = ''

    @classmethod
    def from_dict(cls, data):
        known = {f for f in cls.__dataclass_fields__}
        unknown = set(data) - known
        if unknown:
            raise ValueError('Unknown narrowing keys: %s' % sorted(unknown))
        return cls(**data)

    @classmethod
    def from_yaml(cls, path):
        import yaml
        with open(path, encoding='utf-8') as handle:
            return cls.from_dict(yaml.safe_load(handle) or {})

    def to_dict(self):
        return dict(self.__dict__)

    def with_(self, **changes):
        """A copy with some fields replaced (narrowings are cheap)."""
        return replace(self, **changes)


class FoodDB:
    """The scraped database, plus the search this module exists for."""

    def __init__(self, groups):
        self.groups = dict(sorted(groups.items()))

    # ---------------------------------------------------------------- load

    @classmethod
    def load(cls, path=database.YAML_PATH, root=database.DATA_ROOT):
        """Load ``data.yaml`` if present, else walk the scraped tree."""
        if os.path.exists(path):
            return cls(database.flatten(database.load_yaml(path)))
        return cls(database.load_flat(root=root))

    # ------------------------------------------------------------ browsing

    def summary(self):
        foods = self.all_foods()
        return {
            'groups': len(self.groups),
            'foods': sum(len(v) for v in self.groups.values()),
            'unique_foods': len(foods),
            'sections': sorted({g.split('.')[0] for g in self.groups}),
        }

    def all_foods(self):
        return {food for foods in self.groups.values() for food in foods}

    def group(self, name, drop_noise=False):
        foods = self.groups[name]
        return [f for f in foods if not (drop_noise and is_noise(f))]

    def search_groups(self, *patterns):
        if not patterns:
            return list(self.groups)
        return [g for g in self.groups if matches_any(g, patterns)]

    def search_foods(self, *patterns):
        """``[(group, food), ...]`` for foods matching any pattern."""
        return [
            (group, food)
            for group, foods in self.groups.items()
            for food in foods
            if matches_any(food, patterns)
        ]

    def largest_groups(self, count=20):
        ranked = sorted(self.groups.items(), key=lambda kv: -len(kv[1]))
        return [(name, len(foods)) for name, foods in ranked[:count]]

    # ------------------------------------------------------------ narrowing

    def _pool(self, patterns, narrowing, rng):
        """Candidate ``(group, food)`` pairs for one slot."""
        names = self.search_groups(*patterns) if patterns else list(self.groups)
        if narrowing.include and patterns != narrowing.include:
            names = [n for n in names if matches_any(n, narrowing.include)]
        if narrowing.exclude:
            names = [n for n in names if not matches_any(n, narrowing.exclude)]

        pairs = []
        for name in names:
            # A scraped list can name the same food twice; dedupe so a
            # pair does not come back three times over.
            foods = list(dict.fromkeys(
                f for f in self.groups[name] if self._food_ok(f, narrowing)
            ))
            if narrowing.per_group and len(foods) > narrowing.per_group:
                foods = rng.sample(foods, narrowing.per_group)
            pairs.extend((name, food) for food in foods)
        return pairs

    def _food_ok(self, food, narrowing):
        if narrowing.drop_noise and is_noise(food):
            return False
        if narrowing.include_foods and not matches_any(food, narrowing.include_foods):
            return False
        if narrowing.exclude_foods and matches_any(food, narrowing.exclude_foods):
            return False
        return True

    def _combo_ok(self, items, narrowing):
        foods = [food for _, food in items]
        if len({f.lower() for f in foods}) != len(foods):
            return False
        if narrowing.distinct_groups:
            groups = [group for group, _ in items]
            if len(set(groups)) != len(groups):
                return False
        if narrowing.require_all:
            for needle in narrowing.require_all:
                if not all(contains(food, needle) for food in foods):
                    return False
        if narrowing.require_any:
            for needle in narrowing.require_any:
                if not any(contains(food, needle) for food in foods):
                    return False
        return True

    def slot_pools(self, narrowing):
        """The candidate pool for each slot of ``narrowing``."""
        rng = random.Random(narrowing.seed)
        if narrowing.slots:
            return [self._pool([p], narrowing, rng) for p in narrowing.slots]
        pool = self._pool(narrowing.include, narrowing, rng)
        return [pool] * max(1, narrowing.arity)

    def narrow(self, narrowing=None, score=None, **kwargs):
        """Return combinations satisfying ``narrowing``.

        ``score`` is an optional ``Combo -> number`` ranking function: an
        agent's own plausibility heuristic plugs in here, and the highest
        scores come back first.
        """
        narrowing = narrowing or Narrowing(**kwargs)
        pools = self.slot_pools(narrowing)
        if narrowing.require_all or narrowing.require_any:
            pools = self._focus(pools, narrowing)
        if any(not pool for pool in pools):
            return []

        if _product_size(pools) <= ENUMERATE_CAP:
            return self._enumerate(pools, narrowing, score)
        return self._sample(pools, narrowing, score)

    def _focus(self, pools, narrowing):
        """Shrink slots so ``require_*`` needles are actually reachable.

        Without this a restrictive ``require_any`` would be looking for a
        needle in a haystack the sampler never visits.  Each needle is
        pinned to one slot that can supply it; that loses combinations
        where the same needle turns up in a different slot, which is the
        price of being able to find any at all.
        """
        pools = [list(pool) for pool in pools]
        for needle in narrowing.require_all:
            pools = [
                [pair for pair in pool if contains(pair[1], needle)]
                for pool in pools
            ]
        pinned = set()
        for needle in narrowing.require_any:
            for index, pool in enumerate(pools):
                if index in pinned:
                    continue
                kept = [pair for pair in pool if contains(pair[1], needle)]
                if kept:
                    pools[index] = kept
                    pinned.add(index)
                    break
        return pools

    def _enumerate(self, pools, narrowing, score):
        combos = [
            Combo(items)
            for items in itertools.product(*pools)
            if self._combo_ok(items, narrowing)
        ]
        # Shuffle first so that equal scores come back in a varied order
        # instead of alphabetically by whatever the first slot happened to
        # enumerate.
        random.Random(narrowing.seed).shuffle(combos)
        if score is not None:
            combos.sort(key=score, reverse=True)
        return combos if narrowing.limit is None else combos[:narrowing.limit]

    def _sample(self, pools, narrowing, score):
        """Draw slot-wise when the full product is too large to enumerate."""
        rng = random.Random(narrowing.seed)
        wanted = narrowing.limit or ENUMERATE_CAP
        combos, seen, attempts = [], set(), 0
        while len(combos) < wanted and attempts < 200 * wanted:
            attempts += 1
            items = tuple(rng.choice(pool) for pool in pools)
            if items in seen or not self._combo_ok(items, narrowing):
                continue
            seen.add(items)
            combos.append(Combo(items))
        if score is not None:
            combos.sort(key=score, reverse=True)
        return combos


def shared_token_penalty(combo):
    """Example ``score``: prefer combinations whose names do not overlap.

    Two foods sharing a word ("chocolate cake + chocolate mousse") are
    usually the same idea twice, which is rarely an interesting combo.
    """
    tokens = [set(food.lower().split('_')) for food in combo.foods]
    overlap = sum(
        len(a & b) for a, b in itertools.combinations(tokens, 2)
    )
    return -overlap
