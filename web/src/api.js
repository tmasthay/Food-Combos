// Thin wrapper over the ledger API. Every write carries an actor,
// because "who said this" is the signal the scraper feeds on.

const json = async (response) => {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.error ?? response.statusText);
  return body;
};

const post = (path, payload) =>
  fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).then(json);

const encode = (key) => encodeURIComponent(key);

export const fetchCombos = ({ status = [], order = 'score', actor = '' }) => {
  const params = new URLSearchParams();
  status.forEach((s) => params.append('status', s));
  params.set('order', order);
  if (actor) params.set('actor', actor);
  return fetch(`/api/combos?${params}`).then(json);
};

export const fetchStats = () => fetch('/api/stats').then(json);

export const fetchCombo = (key) => fetch(`/api/combos/${encode(key)}`).then(json);

export const sendVote = (key, actor, value) =>
  post(`/api/combos/${encode(key)}/vote`, { actor, value });

export const sendTrial = (key, actor, verdict, notes) =>
  post(`/api/combos/${encode(key)}/trial`, { actor, verdict, notes });

export const sendReject = (key, actor, reason) =>
  post(`/api/combos/${encode(key)}/reject`, { actor, reason });

export const sendPropose = (actor, foods, rationale) =>
  post('/api/combos', { actor, foods, rationale });

export const wikiUrl = (food) =>
  `https://en.wikipedia.org/wiki/${encodeURIComponent(food.replace(/\\/g, ''))}`;

export const prettyFood = (food) => food.replace(/\\/g, '').replace(/_/g, ' ');
