// Ledger access from Node, via the built-in node:sqlite.
//
// This is the mirror of foodcombos/verdicts.py and obeys the same rule:
// the event table is append-only. There is no UPDATE or DELETE in this
// file, and there should never be one. A changed vote is a new event.

import { DatabaseSync } from 'node:sqlite';
import { existsSync } from 'node:fs';
import { assertSchema, SchemaError, SETTLED, VERDICTS } from './schema.js';

export { SchemaError };

const KINDS = new Set(['propose', 'reject', 'vote', 'trial', 'note']);

export function openLedger(dbPath) {
  if (!existsSync(dbPath)) {
    throw new SchemaError(
      `No ledger at ${dbPath}.\n` +
        'Python owns the schema; create it first:\n' +
        '    python ledger.py init\n' +
        '    python tools/seed_ledger.py   # optional starting material'
    );
  }
  const db = new DatabaseSync(dbPath);
  // WAL so the Python analysis can read while this server writes.
  db.exec('PRAGMA journal_mode=WAL');
  db.exec('PRAGMA foreign_keys=ON');
  assertSchema(db, dbPath);
  return new Ledger(db);
}

// (a, b) and (b, a) are the same plate. Must agree with
// foodcombos.verdicts.combo_key.
export function comboKey(foods) {
  return [...foods].sort().join('|');
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, '+00:00');
}

function hydrate(row) {
  if (!row) return null;
  return {
    ...row,
    foods: JSON.parse(row.foods),
    groups: JSON.parse(row.groups),
    settled: SETTLED.includes(row.status),
  };
}

const ORDERS = {
  score: 'score DESC, first_seen DESC',
  recent: 'first_seen DESC',
  votes: 'ups + downs DESC, score DESC',
};

export class Ledger {
  constructor(db) {
    this.db = db;
  }

  close() {
    this.db.close();
  }

  // --------------------------------------------------------------- reading

  states({ status = [], order = 'score', limit = 200 } = {}) {
    let sql = 'SELECT * FROM combo_state';
    const params = [];
    if (status.length) {
      sql += ` WHERE status IN (${status.map(() => '?').join(',')})`;
      params.push(...status);
    }
    sql += ` ORDER BY ${ORDERS[order] ?? ORDERS.score} LIMIT ?`;
    params.push(limit);
    return this.db
      .prepare(sql)
      .all(...params)
      .map(hydrate);
  }

  state(key) {
    return hydrate(
      this.db.prepare('SELECT * FROM combo_state WHERE combo_key = ?').get(key)
    );
  }

  events(key) {
    return this.db
      .prepare('SELECT * FROM event WHERE combo_key = ? ORDER BY id')
      .all(key)
      .map((e) => ({ ...e, payload: JSON.parse(e.payload) }));
  }

  // What this actor currently thinks, so the UI can show their own vote
  // highlighted rather than guessing.
  myOpinions(actor) {
    const votes = this.db
      .prepare('SELECT combo_key, value FROM vote_current WHERE actor = ?')
      .all(actor);
    const trials = this.db
      .prepare(
        'SELECT combo_key, verdict, notes FROM trial_current WHERE actor = ?'
      )
      .all(actor);
    const out = {};
    for (const v of votes) out[v.combo_key] = { vote: v.value };
    for (const t of trials) {
      out[t.combo_key] = {
        ...(out[t.combo_key] ?? {}),
        trial: t.verdict,
        notes: t.notes,
      };
    }
    return out;
  }

  stats() {
    const byStatus = {};
    for (const row of this.db
      .prepare('SELECT status, COUNT(*) AS n FROM combo_state GROUP BY status')
      .all()) {
      byStatus[row.status] = row.n;
    }
    const events = this.db.prepare('SELECT COUNT(*) AS n FROM event').get().n;
    const actors = this.db
      .prepare('SELECT DISTINCT actor FROM event ORDER BY actor')
      .all()
      .map((r) => r.actor);
    const combos = Object.values(byStatus).reduce((a, b) => a + b, 0);
    return { combos, byStatus, events, actors };
  }

  // --------------------------------------------------------------- writing

  #register(foods, groups) {
    const key = comboKey(foods);
    this.db
      .prepare(
        'INSERT OR IGNORE INTO combo(combo_key, foods, groups, first_seen)' +
          ' VALUES (?, ?, ?, ?)'
      )
      .run(
        key,
        JSON.stringify([...foods].sort()),
        JSON.stringify(groups ?? []),
        nowIso()
      );
    return key;
  }

  // The only write path. Appends; never mutates.
  record({ foods, key, kind, actor, payload = {}, groups = [] }) {
    if (!KINDS.has(kind)) throw new Error(`Unknown event kind: ${kind}`);
    if (!actor) throw new Error('Every event needs an actor');

    let comboId = key;
    if (foods?.length) {
      comboId = this.#register(foods, groups);
    } else {
      const known = this.db
        .prepare('SELECT 1 FROM combo WHERE combo_key = ?')
        .get(comboId);
      if (!known) throw new Error(`Unknown combination: ${comboId}`);
    }

    this.db
      .prepare(
        'INSERT INTO event(ts, combo_key, kind, actor, payload)' +
          ' VALUES (?, ?, ?, ?, ?)'
      )
      .run(nowIso(), comboId, kind, actor, JSON.stringify(payload));
    return comboId;
  }

  propose({ foods, groups, actor, rationale = '' }) {
    return this.record({
      foods,
      groups,
      kind: 'propose',
      actor,
      payload: { rationale },
    });
  }

  reject({ key, foods, actor, reason = '' }) {
    return this.record({ key, foods, kind: 'reject', actor, payload: { reason } });
  }

  vote({ key, foods, actor, value }) {
    const v = Number(value);
    if (![-1, 0, 1].includes(v)) throw new Error('Vote must be -1, 0 or +1');
    return this.record({ key, foods, kind: 'vote', actor, payload: { value: v } });
  }

  trial({ key, foods, actor, verdict, notes = '' }) {
    if (!VERDICTS.includes(verdict)) {
      throw new Error(`Verdict must be one of ${VERDICTS.join(', ')}`);
    }
    return this.record({
      key,
      foods,
      kind: 'trial',
      actor,
      payload: { verdict, notes },
    });
  }

  note({ key, foods, actor, text }) {
    return this.record({ key, foods, kind: 'note', actor, payload: { text } });
  }
}
