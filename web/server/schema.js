// Schema assertions.
//
// Python owns the schema (see foodcombos/verdicts.py). This server is the
// second writer on the same SQLite file, and the failure mode we care
// about is two writers quietly disagreeing about the shape of the data.
// So: assert the version on boot and refuse to serve if it is wrong,
// rather than creating tables we half-understand.

// Must match foodcombos/verdicts.SCHEMA_VERSION.
export const SCHEMA_VERSION = 2;

// Mirrors foodcombos/verdicts.SETTLED.
export const SETTLED = ['rejected', 'tried_bad'];

export const STATUSES = [
  'proposed',
  'rejected',
  'tried_good',
  'tried_bad',
  'tried_mixed',
];

export const VERDICTS = ['good', 'bad', 'mixed'];

// Mirrors foodcombos/verdicts.py. A trial is a 0-100 rating; the verdict
// is derived from it so the band and the number can never disagree.
export const SCORE_MIN = 0;
export const SCORE_MAX = 100;
export const GOOD_AT = 70;
export const BAD_BELOW = 40;

export const FACETS = ['cuisine', 'course', 'technique', 'ingredient'];

export function verdictFor(score) {
  if (score >= GOOD_AT) return 'good';
  if (score < BAD_BELOW) return 'bad';
  return 'mixed';
}

const REQUIRED_TABLES = ['combo', 'event', 'combo_tag'];

const REQUIRED_VIEWS = [
  'combo_state',
  'vote_current',
  'trial_current',
  'propose_first',
  'reject_last',
];

export class SchemaError extends Error {}

export function assertSchema(db, dbPath) {
  let row;
  try {
    row = db
      .prepare("SELECT value FROM schema_meta WHERE key = 'version'")
      .get();
  } catch {
    throw new SchemaError(
      `No ledger schema found in ${dbPath}.\n` +
        'Python owns the schema; create it first:\n' +
        '    python ledger.py init\n' +
        '    python tools/seed_ledger.py   # optional starting material'
    );
  }

  const found = row ? Number(row.value) : null;
  if (found !== SCHEMA_VERSION) {
    throw new SchemaError(
      `Ledger at ${dbPath} is schema version ${found}, but this server ` +
        `speaks ${SCHEMA_VERSION}.\n` +
        'Refusing to start rather than corrupting data. Reconcile ' +
        'foodcombos/verdicts.py and web/server/schema.js deliberately.'
    );
  }

  // Views are recreated by the Python side on every open, so a missing
  // one means the file was built by something else entirely.
  const present = new Set(
    db
      .prepare("SELECT name FROM sqlite_master WHERE type = 'view'")
      .all()
      .map((r) => r.name)
  );
  const tables = new Set(
    db
      .prepare("SELECT name FROM sqlite_master WHERE type = 'table'")
      .all()
      .map((r) => r.name)
  );
  const missing = [
    ...REQUIRED_VIEWS.filter((v) => !present.has(v)),
    ...REQUIRED_TABLES.filter((t) => !tables.has(t)),
  ];
  if (missing.length) {
    throw new SchemaError(
      `Ledger at ${dbPath} is missing: ${missing.join(', ')}.\n` +
        'Run `python ledger.py init` to rebuild them.'
    );
  }
}
