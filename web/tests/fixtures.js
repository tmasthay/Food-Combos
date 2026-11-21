// An isolated app: its own ledger in a temp directory, its own port.
//
// The point is that a test starts from a genuinely empty database rather
// than whatever you happened to click last time. Nothing here touches
// the real combos.db.

import { spawn, spawnSync } from 'node:child_process';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const WEB = resolve(HERE, '..');
const REPO = resolve(WEB, '..');

// Python owns the schema, so the fixture creates the ledger the same way
// a user would. Prefer the venv that has the project's dependencies.
const PYTHONS = [
  resolve(REPO, '..', 'claude_scratch', 'FoodCombos', 'venv', 'Scripts', 'python.exe'),
  'python',
];

function python(args, env) {
  let last;
  for (const exe of PYTHONS) {
    last = spawnSync(exe, args, { cwd: REPO, env, encoding: 'utf8' });
    if (last.status === 0) return last;
    if (last.error?.code !== 'ENOENT') break;
  }
  throw new Error(
    `python ${args.join(' ')} failed:\n${last?.stdout ?? ''}${last?.stderr ?? last?.error}`
  );
}

const waitForHealth = async (port, timeoutMs = 20_000) => {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/api/health`);
      if (r.ok) return await r.json();
    } catch {
      /* not up yet */
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error(`API on ${port} never became healthy`);
};

let nextPort = 8900;

export class TestApp {
  constructor() {
    this.dir = mkdtempSync(join(tmpdir(), 'fc-test-'));
    this.dbPath = join(this.dir, 'combos.db');
    this.port = nextPort++;
    this.origin = `http://127.0.0.1:${this.port}`;
  }

  static async start() {
    const app = new TestApp();
    await app.#boot();
    return app;
  }

  async #boot() {
    const env = { ...process.env, COMBOS_DB: this.dbPath };
    python(['ledger.py', '--db', this.dbPath, 'init'], env);
    this.server = spawn(process.execPath, [join(WEB, 'server', 'index.js')], {
      cwd: WEB,
      env: { ...env, PORT: String(this.port) },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    this.log = '';
    this.server.stdout.on('data', (d) => (this.log += d));
    this.server.stderr.on('data', (d) => (this.log += d));
    await waitForHealth(this.port);
  }

  // Seed combinations straight through the API, as an agent would.
  async propose(foods, { actor = 'agent', rationale = '', groups = [] } = {}) {
    const res = await fetch(`${this.origin}/api/combos`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actor, foods, rationale, groups }),
    });
    if (!res.ok) throw new Error(`propose failed: ${await res.text()}`);
    return res.json();
  }

  // Recompute tags from the scraped lists, the way `ledger.py tag` does.
  tag() {
    python(['ledger.py', '--db', this.dbPath, 'tag'], {
      ...process.env,
      COMBOS_DB: this.dbPath,
    });
  }

  // Seed a rating without driving the browser, for tests whose subject
  // is the aggregate rather than the UI. Keeps each test self-contained
  // so it can be run alone with `-g`.
  async rate(foods, actor, score, notes = '') {
    const key = [...foods].sort().join('|');
    const res = await fetch(
      `${this.origin}/api/combos/${encodeURIComponent(key)}/trial`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actor, score, notes }),
      }
    );
    if (!res.ok) throw new Error(`rate failed: ${await res.text()}`);
    return res.json();
  }

  async combos(query = '') {
    const res = await fetch(`${this.origin}/api/combos${query}`);
    return (await res.json()).combos;
  }

  async state(key) {
    const res = await fetch(
      `${this.origin}/api/combos/${encodeURIComponent(key)}`
    );
    return res.ok ? res.json() : null;
  }

  async stop() {
    this.server?.kill();
    await new Promise((r) => setTimeout(r, 200));
    try {
      rmSync(this.dir, { recursive: true, force: true });
    } catch {
      /* Windows sometimes still holds the WAL; the temp dir can stay */
    }
  }
}

// A browser context per person: separate localStorage means separate
// identities, which is what makes this a multi-user test rather than one
// user clicking a lot.
export async function asUser(browser, origin, name) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(origin);
  await page.fill('.who input', name);
  await page.waitForFunction(
    (who) => localStorage.getItem('actor') === who,
    name
  );
  return { context, page, name };
}

// The ranking formula, mirrored from foodcombos/verdicts.py so the test
// asserts an independently-computed number rather than echoing the app.
export const PRIOR_MEAN = 50;
export const PRIOR_WEIGHT = 3;

export const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;

export const bayes = (xs) =>
  (PRIOR_MEAN * PRIOR_WEIGHT + xs.reduce((a, b) => a + b, 0)) /
  (PRIOR_WEIGHT + xs.length);

export const bandFor = (score) =>
  score >= 70 ? 'tried_good' : score < 40 ? 'tried_bad' : 'tried_mixed';
