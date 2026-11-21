import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ComboCard from './components/ComboCard.jsx';
import {
  fetchCombos,
  fetchStats,
  sendPropose,
  sendReject,
  sendTrial,
  sendVote,
} from './api.js';

// Named views over the ledger, matching the three things this app is for:
// what the agent thinks might work, what it ruled out, and what somebody
// has actually eaten.
const TABS = [
  { id: 'proposed', label: 'Proposed', status: ['proposed'] },
  {
    id: 'tried',
    label: 'Tried',
    status: ['tried_good', 'tried_bad', 'tried_mixed'],
  },
  { id: 'rejected', label: 'Rejected', status: ['rejected'] },
  { id: 'all', label: 'All', status: [] },
];

const ORDERS = [
  { id: 'score', label: 'best' },
  { id: 'recent', label: 'newest' },
  { id: 'votes', label: 'most voted' },
];

export default function App() {
  // The nickname is a label, not a credential -- there is no auth here on
  // purpose (see web/README.md). It just lets the ledger record who said
  // what, which is the part the scraper cares about.
  const [actor, setActor] = useState(() => localStorage.getItem('actor') ?? '');
  const [tab, setTab] = useState('proposed');
  const [order, setOrder] = useState('score');
  const [data, setData] = useState({ combos: [], mine: {} });
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const [draft, setDraft] = useState({ foods: '', rationale: '' });

  useEffect(() => {
    localStorage.setItem('actor', actor);
  }, [actor]);

  const status = useMemo(
    () => TABS.find((t) => t.id === tab)?.status ?? [],
    [tab]
  );

  const reload = useCallback(async () => {
    setBusy(true);
    try {
      const [combos, s] = await Promise.all([
        fetchCombos({ status, order, actor }),
        fetchStats(),
      ]);
      setData(combos);
      setStats(s);
      setError('');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }, [status, order, actor]);

  useEffect(() => {
    reload();
  }, [reload]);

  // Every mutation goes through here so one failure path handles them all
  // and the list always reflects what the ledger actually accepted.
  const act = (fn) => async (...args) => {
    if (!actor.trim()) {
      setError('Type your name first, so the ledger knows who voted.');
      return;
    }
    try {
      await fn(...args);
      await reload();
    } catch (err) {
      setError(err.message);
    }
  };

  const onVote = act((key, value) => sendVote(key, actor, value));
  const onTrial = act((key, verdict, notes) =>
    sendTrial(key, actor, verdict, notes)
  );
  const onReject = act((key, reason) => sendReject(key, actor, reason));

  const onPropose = act(async () => {
    const foods = draft.foods
      .split('+')
      .map((f) => f.trim().replace(/ /g, '_'))
      .filter(Boolean);
    if (foods.length < 2) {
      throw new Error('Give at least two foods, separated by "+".');
    }
    await sendPropose(actor, foods, draft.rationale);
    setDraft({ foods: '', rationale: '' });
  });

  return (
    <div className="app">
      <header>
        <div className="title">
          <h1>Food Combos</h1>
          <p className="sub">
            What the scraper proposed, what got ruled out, and what somebody
            actually ate.
          </p>
        </div>
        <label className="who">
          you are
          <input
            type="text"
            value={actor}
            placeholder="your name"
            onChange={(e) => setActor(e.target.value)}
          />
        </label>
      </header>

      {stats && (
        <div className="stats">
          {Object.entries(stats.byStatus)
            .sort()
            .map(([key, n]) => (
              <span key={key}>
                <strong>{n}</strong> {key.replace('_', ' ')}
              </span>
            ))}
          <span className="dim">{stats.events} events logged</span>
        </div>
      )}

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? 'active' : ''}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
        <span className="spacer" />
        <div className="orders">
          {ORDERS.map((o) => (
            <button
              key={o.id}
              className={order === o.id ? 'active' : ''}
              onClick={() => setOrder(o.id)}
            >
              {o.label}
            </button>
          ))}
        </div>
      </nav>

      <section className="propose">
        <input
          type="text"
          placeholder="Propose one: Katsuobushi + Maple butter"
          value={draft.foods}
          onChange={(e) => setDraft({ ...draft, foods: e.target.value })}
        />
        <input
          type="text"
          placeholder="Why might it work?"
          value={draft.rationale}
          onChange={(e) => setDraft({ ...draft, rationale: e.target.value })}
        />
        <button onClick={onPropose} disabled={!actor.trim()}>
          propose
        </button>
      </section>

      {error && (
        <div className="error" onClick={() => setError('')}>
          {error} <span className="dim">(click to dismiss)</span>
        </div>
      )}

      <main>
        {busy && !data.combos.length ? (
          <p className="dim pad">Loading…</p>
        ) : data.combos.length ? (
          data.combos.map((combo) => (
            <ComboCard
              key={combo.combo_key}
              combo={combo}
              mine={data.mine[combo.combo_key]}
              actor={actor.trim()}
              onVote={onVote}
              onTrial={onTrial}
              onReject={onReject}
            />
          ))
        ) : (
          <p className="dim pad">
            Nothing here yet. Run <code>python tools/seed_ledger.py</code> for
            the agent's first pass, or propose one above.
          </p>
        )}
      </main>

      <footer className="dim">
        Local only · no accounts · the ledger is append-only, so a changed
        vote is a new entry rather than an edit
      </footer>
    </div>
  );
}
