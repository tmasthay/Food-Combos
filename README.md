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

## Cross two lists by hand

```
python cross.py --cartesian --out Queries/coffee_dessert \
    Final/Meals/Sweets/List_of_coffee_dishes/results.txt \
    Final/Meals/Sweets/List_of_desserts/results.txt
```

## GUIs

`nextGen.py` (Qt) and `gui.py` (tkinter) are unmaintained. They read
`data.yaml`; if they break, the scraper and `search.py` do not care.

## Notes

Wikimedia requires a descriptive `User-Agent` and serial, unhurried requests;
`foodcombos/fetch.py` sets one and throttles itself. If you fork this, put your
own contact address in `fetch.USER_AGENT`.
