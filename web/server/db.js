// Ledger access from Node, via the built-in node:sqlite.
//
// This is the mirror of foodcombos/verdicts.py and obeys the same rule:
// the event table is append-only. There is no UPDATE or DELETE in this
// file, and there should never be one. A changed vote is a new event.

import { DatabaseSync } from 'node:sqlite';
import { existsSync } from 'node:fs';
import {
  assertSchema,
  SchemaError,
  SCORE_MAX,
  SCORE_MIN,
  SETTLED,
  verdictFor,
} from './schema.js';

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

function splitTag(tag) {
  const at = tag.indexOf(':');
  if (at < 1) throw new Error(`Tag must look like facet:value, got ${tag}`);
  return [tag.slice(0, at), tag.slice(at + 1)];
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

// 'rating' ranks by the shrunk mean, so a single rave does not outrank
// a well-liked combination several people have cooked. Untried ones sort
// below rated ones rather than vanishing.
const ORDERS = {
  rating: 'bayes_score IS NULL, bayes_score DESC, score DESC',
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

  // `tags` are facet:value strings and narrow rather than widen: a
  // combination must carry every one of them.
  states({ status = [], order = 'rating', limit = 200, tags = [] } = {}) {
    let sql = 'SELECT s.* FROM combo_state s';
    const params = [];
    tags.forEach((tag, index) => {
      const [facet, value] = splitTag(tag);
      const alias = `t${index}`;
      sql +=
        ` JOIN combo_tag ${alias} ON ${alias}.combo_key = s.combo_key` +
        ` AND ${alias}.facet = ? AND ${alias}.value = ?`;
      params.push(facet, value);
    });
    if (status.length) {
      sql += ` WHERE s.status IN (${status.map(() => '?').join(',')})`;
      params.push(...status);
    }
    sql += ` ORDER BY ${ORDERS[order] ?? ORDERS.rating} LIMIT ?`;
    params.push(limit);
    const rows = this.db
      .prepare(sql)
      .all(...params)
      .map(hydrate);
    return this.#withTags(rows);
  }

  #withTags(rows) {
    if (!rows.length) return rows;
    const keys = rows.map((r) => r.combo_key);
    const found = this.db
      .prepare(
        `SELECT combo_key, facet, value FROM combo_tag
         WHERE combo_key IN (${keys.map(() => '?').join(',')})
         ORDER BY facet, value`
      )
      .all(...keys);
    const byKey = new Map(keys.map((k) => [k, []]));
    for (const t of found) byKey.get(t.combo_key)?.push(`${t.facet}:${t.value}`);
    return rows.map((r) => ({ ...r, tags: byKey.get(r.combo_key) ?? [] }));
  }

  tagCounts() {
    const counts = {};
    for (const row of this.db
      .prepare(
        `SELECT facet, value, COUNT(*) AS n FROM combo_tag
         GROUP BY facet, value ORDER BY facet, n DESC, value`
      )
      .all()) {
      (counts[row.facet] ??= []).push({ value: row.value, n: row.n });
    }
    return counts;
  }

  state(key) {
    const row = hydrate(
      this.db.prepare('SELECT * FROM combo_state WHERE combo_key = ?').get(key)
    );
    return row ? this.#withTags([row])[0] : null;
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
        'SELECT combo_key, score, verdict, notes FROM trial_current' +
          ' WHERE actor = ?'
      )
      .all(actor);
    const out = {};
    for (const v of votes) out[v.combo_key] = { vote: v.value };
    for (const t of trials) {
      out[t.combo_key] = {
        ...(out[t.combo_key] ?? {}),
        trial: t.verdict,
        score: t.score,
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

  // A rating out of 100. The verdict is derived, never chosen, so the
  // band shown and the number recorded cannot drift apart.
  trial({ key, foods, actor, score, notes = '' }) {
    const value = Number(score);
    if (!Number.isFinite(value) || value < SCORE_MIN || value > SCORE_MAX) {
      throw new Error(
        `Rating must be a number from ${SCORE_MIN} to ${SCORE_MAX}`
      );
    }
    return this.record({
      key,
      foods,
      kind: 'trial',
      actor,
      payload: { score: value, verdict: verdictFor(value), notes },
    });
  }

  note({ key, foods, actor, text }) {
    return this.record({ key, foods, kind: 'note', actor, payload: { text } });
  }
}
