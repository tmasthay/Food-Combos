# Food-Combos

Scrapes Wikipedia's food lists into a pile of text files, then helps you cross
them looking for combinations nobody has tried.

## Install

```
git clone https://github.com/tmasthay/Food-Combos
cd Food-Combos
pip install -r requirements.txt          # html2text + pyyaml
pip install -r requirements-gui.txt      # only if you want the Qt GUI
```

## Build the database

This walks `Portal:Food`, downloads every food list it links to, and writes one
`results.txt` per list. It takes several minutes and caches as it goes, so an
interrupted run resumes where it stopped. You only need to do it once.

```
python update.py --fetch
python update_yaml.py
```

The result is a tree of plain text plus `data.yaml`:

```
Final/Meals/Sweets/List_of_cakes/results.txt
Final/Meals/origin/List_of_British_breads/results.txt
...
data.yaml
```

Re-parse what's already on disk (fast, no network) with a bare `python
update.py`. The old argument spelling (`python update.py fetch=True`) still
works.

## Search it

**Everything below is offline.** The network is used exactly once, by
`update.py --fetch`; after that the database is a directory of text files plus
`data.yaml`, and searching never opens a socket. `tools/check_offline.py`
enforces that -- it runs the query tools with sockets booby-trapped and the
fetching stack made unimportable, so a stray request *or* a stray import fails
the check.

```
python search.py summary
python search.py groups coffee             # which lists mention coffee
python search.py foods mango               # which lists contain a mango
python search.py largest -n 10

# the main event: one element from a coffee list, one from a dessert list
python search.py combos --slot coffee --slot dessert -n 10 --urls
```

A search can be written down instead of typed, which is the point — a human
narrows the space, an agent judges what comes out. See `narrowing.example.yaml`
and `CLAUDE.md`.

```
python search.py combos --spec narrowing.example.yaml
```

`PLAUSIBLE_COMBOS.md` is a hand-picked set of results from the current
database.

## Vote on them, and record what you actually ate

The scraper can propose; only a person can say whether it was any good.
`combos.db` is where that accumulates, and the search reads it back.

```
python ledger.py init            # create the ledger
python tools/seed_ledger.py      # optional: the agent's first pass

cd web && npm install && npm run dev      # http://127.0.0.1:5173
```

Three views: what was **proposed**, what was **rejected**, what somebody
**tried**. Upvote, downvote, or record a verdict with notes. Local only,
no accounts — the name you type is a label so the ledger can tell an
agent's proposal from a human's verdict. See `web/README.md`.

From the command line, without the app:

```
python ledger.py list --status tried_good
python ledger.py propose Katsuobushi Maple_butter --rationale "inosinate vs caramel"
python ledger.py trial Katsuobushi Maple_butter --good --notes "on sourdough"
python ledger.py export > verdicts.jsonl      # diffable snapshot
```

Searches then skip what's settled:

```
python search.py combos --slot smoked --slot porridge   # hides rejected / tried-bad
python search.py combos --only-new                      # never-seen only
python search.py combos --only-status tried_good        # review what worked
```

## Cross two lists by hand

```
python cross.py --cartesian --out Queries/coffee_dessert \
    Final/Meals/Sweets/List_of_coffee_dishes/results.txt \
    Final/Meals/Sweets/List_of_desserts/results.txt
```

## GUIs

`nextGen.py` (Qt) and `gui.py` (tkinter) are unmaintained. They read
`data.yaml`; if they break, the scraper and `search.py` do not care.

## Dependencies, by what you are doing

| doing | needs |
|---|---|
| `search.py`, `cross.py`, `ledger.py` on an existing database | `pyyaml` (stdlib `sqlite3` for the ledger) |
| `update.py --fetch` -- the one-time download | `html2text` + network |
| the web app | Node 22+ (`node:sqlite` is built in); `npm install` in `web/` |
| the GUIs | `PyQt6` |

## Notes

Wikimedia requires a descriptive `User-Agent` and serial, unhurried requests;
`foodcombos/fetch.py` sets one and throttles itself. If you fork this, put your
own contact address in `fetch.USER_AGENT`.
