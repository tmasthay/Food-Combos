// Local-only API over the verdict ledger.
//
// Scope, deliberately: this binds to 127.0.0.1 and has no authentication.
// It is a tool for one person on one machine, and the "actor" field is a
// label you type, not a credential. Do not expose this to a network
// without adding real auth first -- see web/README.md.

import express from 'express';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import { openLedger, SchemaError } from './db.js';
import { FACETS, STATUSES, SCHEMA_VERSION } from './schema.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '..', '..');

const DB_PATH = process.env.COMBOS_DB ?? resolve(REPO_ROOT, 'combos.db');
const PORT = Number(process.env.PORT ?? 8731);
const HOST = '127.0.0.1'; // local only, not configurable on purpose
const DIST = resolve(HERE, '..', 'dist');

let ledger;
try {
  ledger = openLedger(DB_PATH);
} catch (err) {
  if (err instanceof SchemaError) {
    console.error(`\n${err.message}\n`);
    process.exit(1);
  }
  throw err;
}

const app = express();
app.use(express.json({ limit: '64kb' }));

// Small helper so a thrown error becomes a 400 with a readable message
// instead of an unhandled rejection.
const handle = (fn) => (req, res) => {
  try {
    fn(req, res);
  } catch (err) {
    res.status(400).json({ error: err.message });
  }
};

const requireActor = (req) => {
  const actor = (req.body?.actor ?? '').trim();
  if (!actor) throw new Error('Who are you? An actor name is required.');
  if (actor.length > 40) throw new Error('Actor name is too long.');
  return actor;
};

app.get('/api/health', (_req, res) => {
  res.json({ ok: true, db: DB_PATH, schemaVersion: SCHEMA_VERSION });
});

app.get('/api/stats', handle((_req, res) => res.json(ledger.stats())));

// The facet menu the UI builds its filter chips from.
app.get('/api/tags', handle((_req, res) => res.json(ledger.tagCounts())));

app.get(
  '/api/combos',
  handle((req, res) => {
    const raw = [].concat(req.query.status ?? []);
    const bad = raw.filter((s) => !STATUSES.includes(s));
    if (bad.length) throw new Error(`Unknown status: ${bad.join(', ')}`);
    const actor = (req.query.actor ?? '').trim();
    const tags = [].concat(req.query.tag ?? []);
    const badTags = tags.filter((t) => !FACETS.includes(t.split(':')[0]));
    if (badTags.length) throw new Error(`Unknown facet: ${badTags.join(', ')}`);
    res.json({
      combos: ledger.states({
        status: raw,
        tags,
        order: req.query.order ?? 'rating',
        limit: Math.min(Number(req.query.limit ?? 200), 1000),
      }),
      mine: actor ? ledger.myOpinions(actor) : {},
    });
  })
);

app.get(
  '/api/combos/:key',
  handle((req, res) => {
    const state = ledger.state(req.params.key);
    if (!state) return res.status(404).json({ error: 'No such combination' });
    res.json({ ...state, events: ledger.events(req.params.key) });
  })
);

app.post(
  '/api/combos',
  handle((req, res) => {
    const { foods, groups, rationale } = req.body ?? {};
    if (!Array.isArray(foods) || foods.length < 2) {
      throw new Error('A combination needs at least two foods.');
    }
    const key = ledger.propose({
      foods,
      groups,
      rationale,
      actor: requireActor(req),
    });
    res.status(201).json(ledger.state(key));
  })
);

for (const [path, kind] of [
  ['vote', 'vote'],
  ['trial', 'trial'],
  ['reject', 'reject'],
  ['note', 'note'],
]) {
  app.post(
    `/api/combos/:key/${path}`,
    handle((req, res) => {
      const actor = requireActor(req);
      const { key } = req.params;
      const body = req.body ?? {};
      if (kind === 'vote') ledger.vote({ key, actor, value: body.value });
      else if (kind === 'trial')
        ledger.trial({ key, actor, score: body.score, notes: body.notes });
      else if (kind === 'reject')
        ledger.reject({ key, actor, reason: body.reason });
      else ledger.note({ key, actor, text: body.text });
      res.json(ledger.state(key));
    })
  );
}

// Serve the built UI when it exists; in development Vite serves it and
// proxies /api here instead.
if (existsSync(DIST)) {
  app.use(express.static(DIST));
  app.get(/^(?!\/api\/).*/, (_req, res) =>
    res.sendFile(resolve(DIST, 'index.html'))
  );
}

app.listen(PORT, HOST, () => {
  console.log(`Food-Combos ledger API on http://${HOST}:${PORT}`);
  console.log(`  ledger: ${DB_PATH}`);
  if (!existsSync(DIST)) {
    console.log('  UI:     run `npm run dev` for the Vite dev server');
  }
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    ledger.close();
    process.exit(0);
  });
}
