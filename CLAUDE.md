# CLAUDE.md — Food-Combos

Read this before touching anything here. It is short on purpose.

## What this repo is

A Wikipedia scraper plus a search toy. It walks `Portal:Food`, follows the
`List_of_*` articles the two food navboxes link to, and writes the article
titles it finds into a directory tree of plain text files. Then a human and an
agent use that tree to hunt for food combinations nobody has tried.

There is no database server, no ORM, no SQL, and that is a decision — the data
is ~400 lists and ~20k names, which fits in memory and reads fine as text.
Do not "upgrade" it to SQL.

## Layout

```
foodcombos/
  paths.py      filesystem (sanitizing, Windows long paths, utf-8)
  fetch.py      HTTP (User-Agent, retries, throttle)
  portal.py     Portal:Food  ->  the Final/ tree
  lists.py      one fetched page  ->  results.txt
  scrape.py     orchestration (fetch all, process all)
  database.py   Final/ tree  ->  nested dict / data.yaml
  combos.py     products and random samples
  api.py        narrowed search  <-- the interesting one
  cli.py        shared CLI plumbing
update.py       CLI: scrape
update_yaml.py  CLI: build data.yaml
cross.py        CLI: cross two lists into one file
search.py       CLI: narrowed search
gui.py          old tkinter GUI (unmaintained)
nextGen.py      Qt GUI (unmaintained)
```

**The GUIs are out of scope.** Don't fix them unless asked. `helper.py` exists
only because `gui.py` imports it.

## The data model

```
Final/<navbox>/<row label>/<page title>/
    <page title>_total.txt        the slice of markdown this dir came from
    WebContentsRaw_<title>.txt    the page as served
    WebContentClean_<title>.txt   the page through html2text
    results.txt                   one food per line   <-- the actual payload
```

`<navbox>` is `Cuisines` or `Meals`. `<row label>` is whatever word headed the
navbox table row, so some of them are junk (`eat`, `style`, `deals`) — that is
expected, the labels are scraped, not curated. A directory with no
`results.txt` either wasn't a list page or yielded fewer than
`lists.MIN_RESULTS` foods.

`data.yaml` is that tree as nested dicts with lists at the leaves. A *group* is
one leaf, named with dots: `Meals.Sweets.List_of_cakes`.

## Failure modes that are silent

These cost hours. All four are fixed in the code; don't reintroduce them.

1. **Wikimedia returns HTTP 429 with an error *page*** when the request carries
   no descriptive `User-Agent`. A fetcher that ignores status codes stores 1000
   copies of that error page and prints "Processed 1135 of 1135". This is what
   broke the repo between 2025 and now: 993 of 1135 pages were error pages.
   `fetch.py` sets a UA with a contact address and raises on non-200.
2. **Wikipedia now serves absolute hrefs** (`https://en.wikipedia.org/wiki/X`)
   where it used to serve `/wiki/X`. Regexes that anchor on `(/wiki/` match
   nothing and the scrape silently produces an empty tree. Match both forms.
3. **Windows `MAX_PATH`.** The tree nests past 260 characters. Every open and
   mkdir goes through `paths.long_path`.
4. **cp1252 consoles.** Printing `Jūbako` kills the run mid-scrape. CLI entry
   points call `cli.use_utf8_stdout()`.

Also: non-ASCII titles must be percent-encoded before they reach the network
(`fetch.page_url`), and `…` is not the only character Wikipedia will throw
at you.

## Regression rule

The scrape is the product. When you change parsing, **the new tree must be a
superset of the old one**: every `results.txt` the old code found must still be
found, with at least the same foods. Gaining pages or foods is fine. Losing
them is a bug, even if the code is prettier.

Check it by scraping into a second root and diffing — compare the set of
`results.txt` paths and the set of foods per page, not file timestamps.

## Narrowed search: reading what the human wants

`foodcombos/api.py` exists so a human can hand you a small, declarative
description of *where to look* and you can spend your effort on *judging* what
comes back. The product of two 500-item lists is 250,000 pairs; the human's job
is to cut that to twenty, yours is to say which three are worth cooking.

A **narrowing** is that description. The fields, and what a human means by them:

| field | what the human is telling you |
|---|---|
| `slots` | "one element from a list matching *this*, one from a list matching *that*" — the shape of the combination. `['coffee', 'dessert']` means a coffee thing crossed with a dessert thing. |
| `arity` + `include` | "any N things out of this pool" — used when the slots are interchangeable. |
| `include` / `exclude` | which list pages are in or out of play (patterns on group names). |
| `include_foods` / `exclude_foods` | patterns on individual food names. `exclude_foods: ['*sauce*']` means "stop showing me condiments". |
| `require_any` | at least one element must contain this substring — a theme they're chasing. |
| `require_all` | every element must contain it — usually a narrow experiment. |
| `distinct_groups` | on by default: don't hand back two cakes and call it a pair. |
| `per_group` | thin out fat lists so a 900-item page doesn't swamp a 12-item one. |
| `limit` | how many they want to read. Respect it; twenty is a human-sized list. |
| `seed` | so they can say "number 4 from seed 7" and you can reproduce it. |
| `note` | free text. Read it. It usually contains the actual intent. |

Patterns are globs, case-insensitive, matched against the dotted group name.
A bare word is treated as `*word*`, so `coffee` matches
`Meals.Sweets.List_of_coffee_dishes`.

### What a narrowing is *not*

It does not encode taste, cuisine compatibility, texture, or season. It is a
filter over names, and the names come from Wikipedia, so they are noisy. If the
human writes `slots: ['pickled', 'dessert']` they are not asserting that
pickles belong in dessert — they are asking you to look there and tell them.

### Working a narrowing

```python
from foodcombos.api import FoodDB, Narrowing, shared_token_penalty

db = FoodDB.load()
db.summary()                       # orient yourself
db.search_groups('bread')          # what lists exist
db.group('Meals.origin.List_of_British_breads')

n = Narrowing(slots=['bread', 'preserve'], exclude_foods=['*sauce*'],
              limit=20, seed=7, note='looking for a savoury breakfast')
for combo in db.narrow(n, score=shared_token_penalty):
    print(combo.labelled())
```

Then do the part the code can't:

1. Drop the combinations that are the same food twice under two names
   (`Challah + Egg_bread`), or that are already a standard dish.
2. Keep the ones with a *mechanism* — a reason they'd work. Fat against acid,
   crunch against cream, sweet against salt, a shared aromatic.
3. Report them with the Wikipedia links (`combo.urls()`) and one sentence of
   why, and say which seed and narrowing produced them so the human can go
   back to the same twenty.
4. If a narrowing returns nothing, say which slot had an empty pool
   (`db.slot_pools(n)`) rather than silently widening it. Widening is the
   human's call.

`PLAUSIBLE_COMBOS.md` is a worked example of steps 1–3 over the current
database.

## Conventions

- Python 3.9+, stdlib first. Current third-party deps: `html2text`, `pyyaml`
  (and `PyQt6` only for the unmaintained Qt GUI). Don't add more without
  asking.
- Legacy `key=value` CLI arguments still work (`python update.py fetch=True`);
  the README's commands must keep working.
- Scratch work goes in `claude_scratch/` at the repo *parent*, never inside
  this repo. `Final/`, `data.yaml`, and `Queries/` are generated — don't commit
  them.
