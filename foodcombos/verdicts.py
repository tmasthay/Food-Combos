"""The verdict ledger: what was proposed, rejected, voted on, and eaten.

The scraped word lists in ``Final/`` are read-mostly and regenerable --
throw them away and ``update.py --fetch`` rebuilds them.  This database is
the opposite: it holds judgements a human made, it cannot be
reconstructed from anything, and its whole job is to survive the next
re-scrape.  That difference is why it is SQLite and the scrape is not.

**This module owns the schema.**  The web app (``web/``) reads and writes
the same file through ``node:sqlite``, and asserts :data:`SCHEMA_VERSION`
on boot.  If you change the schema here, bump that constant and teach
``web/server/schema.js`` about it, or the server will refuse to start --
which is the intended outcome, not a bug.

Nothing is ever destructively updated.  ``event`` is append-only; a
changed vote or a corrected verdict is a *new* event, and the current
state is a view over the log.  So the question "what did the agent
actually propose, and why, before anyone argued with it" stays
answerable forever, which is the whole point of feeding this back into
the search.

    >>> ledger = Ledger.open()
    >>> ledger.propose(['Katsuobushi', 'Maple_butter'], actor='agent',
    ...                groups=['Meals.style.List_of_smoked_foods',
    ...                        'Meals.Sweets.List_of_foods_made_from_maple'],
    ...                rationale='inosinate against caramel')
    >>> ledger.vote(['Katsuobushi', 'Maple_butter'], actor='tyler', value=1)
    >>> ledger.state(['Katsuobushi', 'Maple_butter']).status
    'proposed'
"""

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone

DB_PATH = 'combos.db'

#: Bump on any schema change, and update ``web/server/schema.js`` to
#: match.  The web server refuses to start against a version it does not
#: recognise rather than corrupting data it half-understands.
SCHEMA_VERSION = 1

#: Event kinds.  ``propose`` and ``reject`` are what an agent emits after
#: a search; ``vote`` and ``trial`` are what humans emit in the web app.
KINDS = ('propose', 'reject', 'vote', 'trial', 'note')

#: What a trial can conclude.  ``mixed`` is for "works but not like that".
VERDICTS = ('good', 'bad', 'mixed')

TABLES = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Identity registration, not state: a row appears the first time a
-- combination is mentioned and is never updated afterwards.
CREATE TABLE IF NOT EXISTS combo (
    combo_key  TEXT PRIMARY KEY,
    foods      TEXT NOT NULL,            -- JSON array, canonical order
    groups     TEXT NOT NULL,            -- JSON array, parallel to foods
    first_seen TEXT NOT NULL
);

-- The log.  Append-only: no UPDATE or DELETE anywhere in this codebase.
CREATE TABLE IF NOT EXISTS event (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,             -- ISO-8601, UTC
    combo_key TEXT NOT NULL REFERENCES combo(combo_key),
    kind      TEXT NOT NULL,
    actor     TEXT NOT NULL,             -- 'agent', 'tyler', ...
    payload   TEXT NOT NULL DEFAULT '{}',
    CHECK (kind IN ('propose', 'reject', 'vote', 'trial', 'note'))
);

CREATE INDEX IF NOT EXISTS event_combo_idx ON event(combo_key);
CREATE INDEX IF NOT EXISTS event_kind_idx  ON event(kind);
CREATE INDEX IF NOT EXISTS event_ts_idx    ON event(ts);
"""

# Views are derived code, not data: they are dropped and recreated every
# time the ledger is opened, so changing one costs nothing and needs no
# migration.  Only the tables above are durable.
VIEWS = """
DROP VIEW IF EXISTS combo_state;
DROP VIEW IF EXISTS vote_current;
DROP VIEW IF EXISTS trial_current;
DROP VIEW IF EXISTS propose_first;
DROP VIEW IF EXISTS reject_last;

-- One actor, one vote: the newest vote event wins, and a value of 0
-- retracts it.  This is how "I changed my mind" works without an UPDATE.
CREATE VIEW vote_current AS
SELECT combo_key, actor, value FROM (
    SELECT combo_key,
           actor,
           CAST(json_extract(payload, '$.value') AS INTEGER) AS value,
           ROW_NUMBER() OVER (
               PARTITION BY combo_key, actor ORDER BY id DESC
           ) AS rn
    FROM event
    WHERE kind = 'vote'
) WHERE rn = 1 AND value <> 0;

-- Likewise for trials: an actor's latest report on a combination.
CREATE VIEW trial_current AS
SELECT combo_key, actor, verdict, notes, ts FROM (
    SELECT combo_key,
           actor,
           json_extract(payload, '$.verdict') AS verdict,
           json_extract(payload, '$.notes')   AS notes,
           ts,
           ROW_NUMBER() OVER (
               PARTITION BY combo_key, actor ORDER BY id DESC
           ) AS rn
    FROM event
    WHERE kind = 'trial'
) WHERE rn = 1 AND verdict IS NOT NULL;

-- The first time a combination was put forward, and by whom: that is
-- the agent's original claim, and later re-proposals must not overwrite
-- it.  Rejections go the other way -- the most recent one stands.
CREATE VIEW propose_first AS
SELECT combo_key, proposed_by, rationale FROM (
    SELECT combo_key,
           actor                                AS proposed_by,
           json_extract(payload, '$.rationale') AS rationale,
           ROW_NUMBER() OVER (
               PARTITION BY combo_key ORDER BY id ASC
           ) AS rn
    FROM event WHERE kind = 'propose'
) WHERE rn = 1;

CREATE VIEW reject_last AS
SELECT combo_key, rejected_by, reject_reason FROM (
    SELECT combo_key,
           actor                             AS rejected_by,
           json_extract(payload, '$.reason') AS reject_reason,
           ROW_NUMBER() OVER (
               PARTITION BY combo_key ORDER BY id DESC
           ) AS rn
    FROM event WHERE kind = 'reject'
) WHERE rn = 1;

-- Current state of every combination, derived entirely from the log.
--
-- Status precedence, strongest evidence first: somebody who actually
-- cooked the thing outranks somebody who rejected it from the armchair,
-- so a trial always beats a 'reject'.
CREATE VIEW combo_state AS
SELECT
    c.combo_key,
    c.foods,
    c.groups,
    c.first_seen,
    COALESCE(v.ups, 0)        AS ups,
    COALESCE(v.downs, 0)      AS downs,
    COALESCE(v.ups, 0) - COALESCE(v.downs, 0) AS score,
    COALESCE(t.n_trials, 0)   AS n_trials,
    COALESCE(t.n_good, 0)     AS n_good,
    COALESCE(t.n_bad, 0)      AS n_bad,
    COALESCE(t.n_mixed, 0)    AS n_mixed,
    p.proposed_by,
    p.rationale,
    r.rejected_by,
    r.reject_reason,
    CASE
        WHEN COALESCE(t.n_trials, 0) > 0 THEN
            CASE
                WHEN t.n_good > 0 AND t.n_bad = 0 THEN 'tried_good'
                WHEN t.n_bad > 0 AND t.n_good = 0 THEN 'tried_bad'
                ELSE 'tried_mixed'
            END
        WHEN r.rejected_by IS NOT NULL THEN 'rejected'
        ELSE 'proposed'
    END AS status
FROM combo c
LEFT JOIN (
    SELECT combo_key,
           SUM(CASE WHEN value > 0 THEN 1 ELSE 0 END) AS ups,
           SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) AS downs
    FROM vote_current GROUP BY combo_key
) v ON v.combo_key = c.combo_key
LEFT JOIN (
    SELECT combo_key,
           COUNT(*) AS n_trials,
           SUM(CASE WHEN verdict = 'good'  THEN 1 ELSE 0 END) AS n_good,
           SUM(CASE WHEN verdict = 'bad'   THEN 1 ELSE 0 END) AS n_bad,
           SUM(CASE WHEN verdict = 'mixed' THEN 1 ELSE 0 END) AS n_mixed
    FROM trial_current GROUP BY combo_key
) t ON t.combo_key = c.combo_key
LEFT JOIN propose_first p ON p.combo_key = c.combo_key
LEFT JOIN reject_last   r ON r.combo_key = c.combo_key;
"""

#: Statuses the search should stop re-proposing.  A rejected combination
#: and one that was cooked and disliked are both settled questions.
SETTLED = ('rejected', 'tried_bad')


def combo_key(foods):
    """Canonical identity for a combination, order-independent.

    ``(a, b)`` and ``(b, a)`` are the same plate, so the key is the
    sorted members joined by a character that cannot occur in a
    Wikipedia title.
    """
    return '|'.join(sorted(foods))


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass
class ComboState:
    """A row of ``combo_state``, as something with attributes."""

    combo_key: str
    foods: list = field(default_factory=list)
    groups: list = field(default_factory=list)
    first_seen: str = ''
    ups: int = 0
    downs: int = 0
    score: int = 0
    n_trials: int = 0
    n_good: int = 0
    n_bad: int = 0
    n_mixed: int = 0
    proposed_by: str = None
    rationale: str = None
    rejected_by: str = None
    reject_reason: str = None
    status: str = 'proposed'

    @classmethod
    def from_row(cls, row):
        data = dict(row)
        data['foods'] = json.loads(data['foods'])
        data['groups'] = json.loads(data['groups'])
        return cls(**data)

    @property
    def settled(self):
        return self.status in SETTLED

    def pretty(self):
        return ' + '.join(f.replace('_', ' ') for f in self.foods)


class Ledger:
    """Append-only access to the verdict database."""

    def __init__(self, connection):
        self.db = connection
        self.db.row_factory = sqlite3.Row

    # ------------------------------------------------------------- opening

    @classmethod
    def open(cls, path=DB_PATH, create=True):
        """Open (and if needed create) the ledger at ``path``."""
        if not create and not os.path.exists(path):
            raise FileNotFoundError(path)
        connection = sqlite3.connect(path)
        ledger = cls(connection)
        ledger._migrate()
        return ledger

    def _migrate(self):
        # WAL lets the Python analysis read while the web app writes.
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(TABLES)
        self.db.executescript(VIEWS)
        found = self.version()
        if found is None:
            self.db.execute(
                'INSERT INTO schema_meta(key, value) VALUES (?, ?)',
                ('version', str(SCHEMA_VERSION)),
            )
            self.db.commit()
        elif found != SCHEMA_VERSION:
            raise RuntimeError(
                'Ledger at schema version %s, this code speaks %s. '
                'Migrate deliberately rather than letting two writers '
                'disagree about the shape of the data.'
                % (found, SCHEMA_VERSION)
            )

    def version(self):
        row = self.db.execute(
            "SELECT value FROM schema_meta WHERE key = 'version'"
        ).fetchone()
        return int(row['value']) if row else None

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------- writing

    def _register(self, foods, groups=None):
        key = combo_key(foods)
        self.db.execute(
            'INSERT OR IGNORE INTO combo(combo_key, foods, groups, first_seen)'
            ' VALUES (?, ?, ?, ?)',
            (
                key,
                json.dumps(sorted(foods)),
                json.dumps(list(groups) if groups else []),
                now(),
            ),
        )
        return key

    def record(self, foods, kind, actor, payload=None, groups=None):
        """Append one event.  The only write path in this module."""
        if kind not in KINDS:
            raise ValueError('Unknown event kind: %r' % kind)
        if not actor:
            raise ValueError('Every event needs an actor')
        key = self._register(foods, groups)
        cursor = self.db.execute(
            'INSERT INTO event(ts, combo_key, kind, actor, payload)'
            ' VALUES (?, ?, ?, ?, ?)',
            (now(), key, kind, actor, json.dumps(payload or {})),
        )
        self.db.commit()
        return cursor.lastrowid

    def propose(self, foods, actor='agent', groups=None, rationale='',
                narrowing=None):
        """An agent (or a human) puts a combination forward."""
        payload = {'rationale': rationale}
        if narrowing is not None:
            payload['narrowing'] = narrowing
        return self.record(foods, 'propose', actor, payload, groups)

    def reject(self, foods, actor='agent', groups=None, reason=''):
        """Judged implausible without being cooked."""
        return self.record(foods, 'reject', actor, {'reason': reason}, groups)

    def vote(self, foods, actor, value, groups=None):
        """``+1``, ``-1``, or ``0`` to retract."""
        value = int(value)
        if value not in (-1, 0, 1):
            raise ValueError('Vote must be -1, 0 or +1')
        return self.record(foods, 'vote', actor, {'value': value}, groups)

    def trial(self, foods, actor, verdict, notes='', groups=None):
        """Somebody actually ate it."""
        if verdict not in VERDICTS:
            raise ValueError('Verdict must be one of %s' % (VERDICTS,))
        return self.record(
            foods, 'trial', actor, {'verdict': verdict, 'notes': notes}, groups
        )

    def note(self, foods, actor, text, groups=None):
        return self.record(foods, 'note', actor, {'text': text}, groups)

    # ------------------------------------------------------------- reading

    def state(self, foods):
        """Current state of one combination, or ``None`` if unknown."""
        row = self.db.execute(
            'SELECT * FROM combo_state WHERE combo_key = ?',
            (combo_key(foods),),
        ).fetchone()
        return ComboState.from_row(row) if row else None

    def states(self, status=None, limit=None, order='score'):
        """Every combination, newest-first or best-first."""
        orders = {
            'score': 'score DESC, first_seen DESC',
            'recent': 'first_seen DESC',
            'votes': 'ups + downs DESC, score DESC',
        }
        sql = 'SELECT * FROM combo_state'
        params = []
        if status:
            placeholders = ','.join('?' * len(status))
            sql += ' WHERE status IN (%s)' % placeholders
            params.extend(status)
        sql += ' ORDER BY %s' % orders.get(order, orders['score'])
        if limit:
            sql += ' LIMIT ?'
            params.append(limit)
        return [
            ComboState.from_row(r) for r in self.db.execute(sql, params)
        ]

    def settled_keys(self):
        """Keys the search should stop offering.

        One indexed query, loaded once per search rather than per
        candidate pair -- the set is small and the search is hot.
        """
        return {
            row['combo_key']
            for row in self.db.execute(
                'SELECT combo_key FROM combo_state WHERE status IN (%s)'
                % ','.join('?' * len(SETTLED)),
                SETTLED,
            )
        }

    def known_keys(self):
        """Every key the ledger has ever heard of, settled or not."""
        return {
            row['combo_key']
            for row in self.db.execute('SELECT combo_key FROM combo')
        }

    def status_map(self):
        """``{combo_key: status}`` for annotating search results."""
        return {
            row['combo_key']: row['status']
            for row in self.db.execute(
                'SELECT combo_key, status FROM combo_state'
            )
        }

    def events(self, foods=None, limit=None):
        """The raw log, for export and for auditing what happened."""
        sql = 'SELECT * FROM event'
        params = []
        if foods is not None:
            sql += ' WHERE combo_key = ?'
            params.append(combo_key(foods))
        sql += ' ORDER BY id'
        if limit:
            sql += ' LIMIT ?'
            params.append(limit)
        return [dict(r) for r in self.db.execute(sql, params)]

    def stats(self):
        counts = {
            row['status']: row['n']
            for row in self.db.execute(
                'SELECT status, COUNT(*) AS n FROM combo_state GROUP BY status'
            )
        }
        total_events = self.db.execute(
            'SELECT COUNT(*) AS n FROM event'
        ).fetchone()['n']
        actors = [
            row['actor']
            for row in self.db.execute(
                'SELECT DISTINCT actor FROM event ORDER BY actor'
            )
        ]
        return {
            'combos': sum(counts.values()),
            'by_status': counts,
            'events': total_events,
            'actors': actors,
            'schema_version': self.version(),
        }

    # ------------------------------------------------------------ exporting

    def export_jsonl(self):
        """The log as JSONL -- diffable, reviewable, committable."""
        lines = []
        for event in self.events():
            event['payload'] = json.loads(event['payload'])
            lines.append(json.dumps(event, sort_keys=True))
        return '\n'.join(lines)
