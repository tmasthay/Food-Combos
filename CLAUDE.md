# CLAUDE.md — Food-Combos

Read this before touching anything here. It is short on purpose.

## What this repo is

A Wikipedia scraper plus a search toy. It walks `Portal:Food`, follows the
`List_of_*` articles the two food navboxes link to, and writes the article
titles it finds into a directory tree of plain text files. Then a human and an
agent use that tree to hunt for food combinations nobody has tried.

**The scraped data is plain text and stays that way.** ~400 lists and ~20k
names fit in memory and read fine as files; there is no ORM and no SQL over
them, and that is a decision. Don't "upgrade" `Final/` or `data.yaml` to a
database.

**The verdict ledger is SQLite, and that is also a decision.** `combos.db`
holds what humans judged — votes, trials, rejections. It is irreplaceable
(nothing can regenerate it), it has two concurrent writers, and the search
queries it per candidate pair. Those are the problems a database solves.
Don't "simplify" it back to flat files. See `foodcombos/verdicts.py`.

## Layout

```
foodcombos/
  paths.py      filesystem (sanitizing, Windows long paths, utf-8)
  verdicts.py   the verdict ledger (SQLite) -- OWNS THE SCHEMA
  wiki.py       title -> URL (stdlib only; safe to import from anywhere)
  fetch.py      HTTP (User-Agent, retries, throttle)  <-- the only network
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
ledger.py       CLI: read/write verdicts
web/            local React app for voting and recording trials
tools/
  compare_trees.py   regression check: new scrape vs old
  check_offline.py   asserts the query tools never touch the network
  seed_ledger.py     loads PLAUSIBLE_COMBOS.md into the ledger
gui.py          old tkinter GUI (unmaintained)
nextGen.py      Qt GUI (unmaintained)
```

**The GUIs are out of scope.** Don't fix them unless asked. `helper.py` exists
only because `gui.py` imports it.

## Online once, offline after

The network is touched in exactly one place: `foodcombos/fetch.py`, reached
only by `update.py --fetch` (and `cross.py --update`, which calls the same
thing). That run is bandwidth-bound and slow -- about 1100 pages, several
minutes, throttled on purpose -- and it caches, so it is a one-time cost.

Everything after it reads the local `Final/` tree or `data.yaml`:
`search.py`, `foodcombos/api.py`, `foodcombos/database.py`,
`foodcombos/combos.py`, `cross.py` without `--update`, and `update.py` without
`--fetch` (which re-parses pages already on disk). None of them open a socket.

This is a guarantee, not an accident, and it is enforced:

```
python tools/check_offline.py
```

That runs the query tools with `socket.socket`, `create_connection` and
`getaddrinfo` replaced by exceptions *and* with `html2text`, `urllib.request`
and `http.client` made unimportable. Keep it passing. Concretely:

- `foodcombos/wiki.py` holds title-to-URL formatting and is stdlib-only, so
  the search path can print Wikipedia links without importing the fetcher.
  Import `page_url` from there, never from `fetch`.
- Don't add a module-level `from .fetch import ...` (or anything that pulls it
  in) to `api.py`, `database.py`, `combos.py`, or `cross.py`. `cross.py`
  imports `scrape.run` lazily inside its `--update` branch for this reason.
- If a search ever needs data that isn't scraped yet, the answer is to widen
  the scrape and re-run the one-time download -- not to fetch at query time.

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
(`wiki.page_url`), and `…` is not the only character Wikipedia will throw
at you.

## Regression rule

The scrape is the product. When you change parsing, **the new tree must be a
superset of the old one**: every `results.txt` the old code found must still be
found, with at least the same foods. Gaining pages or foods is fine. Losing
them is a bug, even if the code is prettier.

Check it by scraping into a second root and diffing — compare the set of
`results.txt` paths and the set of foods per page, not file timestamps.

## The verdict loop

The scrape tells you what foods exist. It cannot tell you whether a
combination is good, and neither can you — only somebody who cooked it
knows. `combos.db` is where that knowledge accumulates, and it is the
reason the next pass is smarter than the last one.

Four event kinds, append-only:

| kind | who emits it | means |
|---|---|---|
| `propose` | usually you | "this might work, here's the mechanism" |
| `reject` | usually you | "ruled out, here's why" — without cooking it |
| `vote` | humans, in the web app | a hunch, cheap to give |
| `trial` | humans, in the web app | somebody actually ate it |

A *trial outranks a rejection*: armchair reasoning loses to a fork. And
the newest event from one actor wins, so a changed vote is a new row,
never an edit. The whole history stays readable:

```
python ledger.py log Katsuobushi Maple_butter
```

### Your side of the loop

After a search, write down what you concluded — both halves. The
rejections matter as much as the proposals, because they're what stops
the next pass re-offering the same dead ends:

```
python ledger.py propose Katsuobushi Maple_butter     --rationale "inosinate against caramel; bacon-and-maple without the fat"
python ledger.py reject Paprika Tsampa     --reason "paprika is an ingredient, not a thing you pair with porridge"
```

Then `search.py` consults the ledger automatically:

```
python search.py combos --slot smoked --slot porridge   # settled ones hidden
python search.py combos --only-new                      # never-seen only
python search.py combos --only-status tried_good        # review what worked
python search.py combos --include-settled               # see them anyway
```

`rejected` and `tried_bad` are *settled* and suppressed by default.
`tried_good` is not suppressed — a combination that worked is worth
building on, and results carry a `<tried_good>` tag so you can see it.

Two constants have to agree: `api.SETTLED_STATUSES` mirrors
`verdicts.SETTLED` by hand, because `api.py` must not import the ledger
at module scope (see the offline rule above). `tools/check_offline.py`
asserts they match.

### Reading the ledger before you search

Check what's already been judged before spending a search on it:

```
python ledger.py stats
python ledger.py list --status tried_good
python ledger.py list --status rejected
```

If a human tried something and liked it, the interesting next move is
usually a *variation* on it, not a fresh random pair — swap one element
and keep the mechanism. If they disliked it, the mechanism you claimed
was probably wrong; say so in the next rationale rather than quietly
proposing a near-duplicate.

### Don't

- Don't `UPDATE` or `DELETE` in `combos.db`. Ever. Correct a mistake by
  appending the correcting event.
- Don't propose in bulk. Twenty machine-generated proposals with no
  rationale is noise a human has to clear. Propose what you can argue for.
- Don't edit the schema on the Node side. Python owns it; bump
  `SCHEMA_VERSION` in both places or the server refuses to start.

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
