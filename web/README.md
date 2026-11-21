# Food-Combos web app

A local app for the half of this project a scraper cannot do: deciding
whether a combination is actually any good.

It shows three things — what the agent **proposed**, what it **rejected**,
and what somebody has actually **tried** — and writes your votes and
verdicts back into a ledger the scraper reads on its next pass.

## Run it

The ledger must exist first; Python owns the schema.

```
python ledger.py init            # from the repo root
python tools/seed_ledger.py      # optional: the agent's first pass
python ledger.py tag             # derive the facet tags
```

Then:

```
cd web
npm install
npm run dev        # http://127.0.0.1:5173
```

`npm run dev` runs the API (port 8731) and the Vite dev server (5173)
together; Vite proxies `/api` so the browser sees one origin. For a
single process serving the built UI:

```
npm run build && npm start     # http://127.0.0.1:8731
```

## Scope

This binds to `127.0.0.1` and has **no authentication**. The name you
type is a label, not a credential — it exists so the ledger can record
that the agent proposed something and a human disagreed, which is the
distinction the search feeds on. That is the right trade for a tool
running on one machine.

Before this ever faces a network it would need real accounts, a session
story, and write authorization. None of that is built, and none of it
should be built until it's actually needed.

## Layout

```
server/
  index.js    express routes, binds 127.0.0.1
  db.js       node:sqlite access -- append-only, no UPDATE/DELETE
  schema.js   version assertion; mirrors foodcombos/verdicts.py
src/
  App.jsx             tabs, identity, the reload cycle
  api.js              fetch wrappers
  components/
    ComboCard.jsx     one combination: votes, verdict, rationale
  style.css
```

The database needs no npm package — Node 22+ ships `node:sqlite`, so the
only runtime dependency here is Express.

## Two writers, one file

Python and Node both write `combos.db`. The rules that keep that safe:

1. **Python owns the schema.** `foodcombos/verdicts.py` creates tables and
   views; this server only asserts `SCHEMA_VERSION` and refuses to start
   on a mismatch. If you change the schema, bump it in *both* places.
2. **WAL mode**, so the Python analysis can read while the app writes.
3. **Append-only.** Neither side ever UPDATEs or DELETEs an event. A
   changed vote is a new row; current state is a view over the log. This
   is why "what did the agent originally claim, before anyone argued"
   stays answerable.

## API

All routes are under `/api`. Writes require an `actor` in the body.

| method | route | does |
|---|---|---|
| GET | `/api/health` | db path and schema version |
| GET | `/api/stats` | counts by status, event total, actors |
| GET | `/api/tags` | facet menu with counts |
| GET | `/api/combos?status=&tag=&order=&actor=` | list, plus that actor's own votes |
| GET | `/api/combos/:key` | one combination and its full event log |
| POST | `/api/combos` | propose `{actor, foods[], rationale}` |
| POST | `/api/combos/:key/vote` | `{actor, value}` — `+1`, `-1`, `0` to retract |
| POST | `/api/combos/:key/trial` | `{actor, score, notes}` — score is 0–100 |
| POST | `/api/combos/:key/reject` | `{actor, reason}` |

`:key` is the canonical combination key: member foods sorted and joined
with `|`, URL-encoded. The same key Python uses.

## Ratings

A trial is a **0–100 score**; the good/mixed/bad band is derived from it
(`>=70` / `<40` / between) so the colour and the number cannot disagree.
Votes stayed binary: a vote is a cheap hunch about something nobody has
cooked, a rating is earned, and they should not cost the same.

Two aggregates, deliberately:

- `mean_score` — the plain average. Shown on the card, decides the band.
- `bayes_score` — shrunk toward 50 by three pseudo-ratings,
  `(50*3 + Σscores) / (3 + n)`. Used only for ranking, so a single rave
  doesn't outrank a tested favourite.

## Facets

Tags are derived from the list pages a food came from, not typed in:
`cuisine`, `course`, `technique`, `ingredient`. Chips filter the list and
**intersect** — korean *and* dessert, not either. Rebuild them with
`python ledger.py tag` after adding combinations.

## Tests

```
npm test                 # all of them
npm test -- -g "lone rave"
npm run test:headed      # watch it happen
```

Playwright, using the Edge already on the machine (no browser download).
Each test gets its **own ledger in a temp directory and its own port**,
so nothing touches your real `combos.db`, and each is self-contained
enough to run alone.

The multi-user tests open a browser context per person — separate
`localStorage`, so genuinely separate identities — and every expected
number is computed from the formula in the test rather than read back
from the app. That means changing the aggregation breaks a test instead
of silently agreeing with itself.

## What the scraper does with this

Covered in the repo's `CLAUDE.md`. Short version: a rejected combination
and one that was cooked and disliked are settled questions, and
`search.py` stops offering them.

```
python search.py combos --slot smoked --slot porridge
python search.py combos --only-new          # never-seen only
python search.py combos --only-status tried_good
```
