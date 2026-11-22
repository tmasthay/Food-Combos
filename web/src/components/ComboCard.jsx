import React, { useState } from 'react';
import { prettyFood, verdictFor, wikiUrl } from '../api.js';

const STATUS_LABEL = {
  proposed: 'proposed',
  rejected: 'rejected',
  tried_good: 'good',
  tried_bad: 'bad',
  tried_mixed: 'mixed',
};

export default function ComboCard({
  combo,
  mine,
  actor,
  onVote,
  onTrial,
  onReject,
  onTagClick,
  activeTags = [],
}) {
  const [open, setOpen] = useState(false);
  // Default the slider to your previous rating if you have one, so
  // "change my mind" starts from where you left off rather than 50.
  const [score, setScore] = useState(mine?.score ?? 50);
  const [notes, setNotes] = useState(mine?.notes ?? '');
  const [reason, setReason] = useState('');
  const myVote = mine?.vote ?? 0;

  // Clicking your own vote again retracts it, which is what the 0 value
  // in the ledger is for.
  const vote = (value) => onVote(combo.combo_key, myVote === value ? 0 : value);
  const rated = combo.n_trials > 0;

  return (
    <article className={`card status-${combo.status}`}>
      <div className="card-main">
        <div className="gutter">
          {rated ? (
            <div
              className={`rating rating-${verdictFor(combo.mean_score)}`}
              title={`mean of ${combo.n_trials} rating${
                combo.n_trials > 1 ? 's' : ''
              }, ${Math.round(combo.min_score)}–${Math.round(combo.max_score)}`}
            >
              <span className="rating-number">
                {Math.round(combo.mean_score)}
              </span>
              <span className="rating-n">n={combo.n_trials}</span>
            </div>
          ) : (
            <div className="rating rating-none" title="nobody has cooked it">
              <span className="rating-number">–</span>
              <span className="rating-n">untried</span>
            </div>
          )}
          <div className="votes">
            <button
              className={`vote up ${myVote > 0 ? 'active' : ''}`}
              onClick={() => vote(1)}
              disabled={!actor}
              title={actor ? 'Worth trying' : 'Enter your name first'}
            >
              ▲
            </button>
            <span className="score">
              {combo.score > 0 ? `+${combo.score}` : combo.score}
            </span>
            <button
              className={`vote down ${myVote < 0 ? 'active' : ''}`}
              onClick={() => vote(-1)}
              disabled={!actor}
              title={actor ? 'Not worth trying' : 'Enter your name first'}
            >
              ▼
            </button>
          </div>
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
            {combo.proposed_by && <span>by {combo.proposed_by}</span>}
            {rated && combo.n_trials > 1 && (
              <span>
                spread {Math.round(combo.min_score)}–
                {Math.round(combo.max_score)}
              </span>
            )}
          </div>

          {combo.tags?.length > 0 && (
            <div className="tags">
              {combo.tags.map((tag) => (
                <button
                  key={tag}
                  className={`tag tag-${tag.split(':')[0]} ${
                    activeTags.includes(tag) ? 'on' : ''
                  }`}
                  onClick={() => onTagClick(tag)}
                  title={`filter by ${tag}`}
                >
                  {tag.split(':')[1].replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          )}

          {combo.rationale && <p className="rationale">{combo.rationale}</p>}
          {combo.reject_reason && (
            <p className="reason">
              ruled out by {combo.rejected_by}: {combo.reject_reason}
            </p>
          )}
        </div>
      </div>

      <div className="actions">
        {mine?.score != null && (
          <span className="mine">
            you rated this <strong>{Math.round(mine.score)}</strong>
          </span>
        )}
        <button className="link" onClick={() => setOpen(!open)} disabled={!actor}>
          {open ? 'cancel' : mine?.score != null ? 'change rating' : 'I tried this'}
        </button>
      </div>

      {open && (
        <div className="trial-form">
          <label className="slider-row">
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={score}
              onChange={(e) => setScore(Number(e.target.value))}
              aria-label="rating out of 100"
            />
            <output className={`slider-value rating-${verdictFor(score)}`}>
              {score}
            </output>
          </label>
          <input
            type="text"
            placeholder="How was it? (optional notes)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <button
            className={`submit rating-${verdictFor(score)}`}
            onClick={() => {
              onTrial(combo.combo_key, score, notes);
              setOpen(false);
            }}
          >
            record {score}/100
          </button>
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
