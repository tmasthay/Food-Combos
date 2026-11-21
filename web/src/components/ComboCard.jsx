import React, { useState } from 'react';
import { prettyFood, wikiUrl } from '../api.js';

const STATUS_LABEL = {
  proposed: 'proposed',
  rejected: 'rejected',
  tried_good: 'tried — good',
  tried_bad: 'tried — bad',
  tried_mixed: 'tried — mixed',
};

export default function ComboCard({ combo, mine, actor, onVote, onTrial, onReject }) {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState(mine?.notes ?? '');
  const [reason, setReason] = useState('');
  const myVote = mine?.vote ?? 0;
  const myTrial = mine?.trial;

  // Clicking your own vote again retracts it, which is what the 0 value
  // in the ledger is for.
  const vote = (value) => onVote(combo.combo_key, myVote === value ? 0 : value);

  return (
    <article className={`card status-${combo.status}`}>
      <div className="card-main">
        <div className="votes">
          <button
            className={`vote up ${myVote > 0 ? 'active' : ''}`}
            onClick={() => vote(1)}
            disabled={!actor}
            title={actor ? 'Upvote' : 'Enter your name first'}
          >
            ▲
          </button>
          <span className="score">{combo.score > 0 ? `+${combo.score}` : combo.score}</span>
          <button
            className={`vote down ${myVote < 0 ? 'active' : ''}`}
            onClick={() => vote(-1)}
            disabled={!actor}
            title={actor ? 'Downvote' : 'Enter your name first'}
          >
            ▼
          </button>
        </div>

        <div className="body">
          <h3>
            {combo.foods.map((food, i) => (
              <React.Fragment key={food}>
                {i > 0 && <span className="plus"> + </span>}
                <a href={wikiUrl(food)} target="_blank" rel="noreferrer">
                  {prettyFood(food)}
                </a>
              </React.Fragment>
            ))}
          </h3>

          <div className="meta">
            <span className={`badge badge-${combo.status}`}>
              {STATUS_LABEL[combo.status] ?? combo.status}
            </span>
            {combo.proposed_by && <span>proposed by {combo.proposed_by}</span>}
            {combo.n_trials > 0 && (
              <span>
                {combo.n_good}&nbsp;good · {combo.n_bad}&nbsp;bad
                {combo.n_mixed > 0 && ` · ${combo.n_mixed} mixed`}
              </span>
            )}
            {combo.groups?.length > 0 && (
              <span className="groups">
                {combo.groups.map((g) => g.split('.').pop()).join(' × ')}
              </span>
            )}
          </div>

          {combo.rationale && <p className="rationale">{combo.rationale}</p>}
          {combo.reject_reason && (
            <p className="reason">
              rejected by {combo.rejected_by}: {combo.reject_reason}
            </p>
          )}
        </div>
      </div>

      <div className="actions">
        {myTrial ? (
          <span className="mine">
            you tried this: <strong>{myTrial}</strong>
          </span>
        ) : null}
        <button className="link" onClick={() => setOpen(!open)} disabled={!actor}>
          {open ? 'cancel' : myTrial ? 'change verdict' : 'I tried this'}
        </button>
      </div>

      {open && (
        <div className="trial-form">
          <input
            type="text"
            placeholder="How was it? (optional notes)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="trial-buttons">
            {['good', 'mixed', 'bad'].map((verdict) => (
              <button
                key={verdict}
                className={`verdict verdict-${verdict}`}
                onClick={() => {
                  onTrial(combo.combo_key, verdict, notes);
                  setOpen(false);
                }}
              >
                {verdict}
              </button>
            ))}
          </div>
          <div className="reject-row">
            <input
              type="text"
              placeholder="…or rule it out without cooking it, and why"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button
              className="link danger"
              disabled={!reason.trim()}
              onClick={() => {
                onReject(combo.combo_key, reason);
                setOpen(false);
                setReason('');
              }}
            >
              reject
            </button>
          </div>
        </div>
      )}
    </article>
  );
}
