// frontend/src/components/LiveScoreCard.jsx
import React from 'react'

/**
 * LiveScoreCard — displays a single live game's current state.
 *
 * Props:
 *   game {object} — live_scores row from /api/live
 */
export default function LiveScoreCard({ game }) {
  const {
    home_team, away_team,
    home_score, away_score,
    quarter, time_remaining,
    last_scorer, last_play_description,
    updated_at,
  } = game

  const isLeading = home_score > away_score
  const isTied    = home_score === away_score

  return (
    <div
      className="glass-card p-5 flex flex-col gap-4 animate-fade-in"
      style={{
        borderColor: 'rgba(16,185,129,0.25)',
        boxShadow:   '0 4px 24px rgba(16,185,129,0.1)',
      }}
    >
      {/* Live indicator + quarter */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="live-dot" aria-hidden="true" />
          <span className="text-emerald text-xs font-semibold tracking-widest uppercase">Live</span>
        </div>
        <span className="text-xs text-muted font-mono">
          Q{quarter} · {time_remaining}
        </span>
      </div>

      {/* Scoreboard */}
      <div className="flex items-center justify-between gap-2">
        {/* Home */}
        <div className="flex-1 text-center">
          <p className="text-xs text-muted truncate mb-1">{home_team ?? 'HOME'}</p>
          <p
            className="text-5xl font-extrabold leading-none"
            style={{
              fontFamily: '"Barlow Condensed", sans-serif',
              color: !isTied && isLeading ? '#10b981' : '#e0f2fe',
            }}
          >
            {home_score ?? 0}
          </p>
        </div>

        {/* VS divider */}
        <div className="flex flex-col items-center gap-1 px-2">
          <span className="text-muted text-lg font-bold">VS</span>
        </div>

        {/* Away */}
        <div className="flex-1 text-center">
          <p className="text-xs text-muted truncate mb-1">{away_team ?? 'AWAY'}</p>
          <p
            className="text-5xl font-extrabold leading-none"
            style={{
              fontFamily: '"Barlow Condensed", sans-serif',
              color: !isTied && !isLeading ? '#10b981' : '#e0f2fe',
            }}
          >
            {away_score ?? 0}
          </p>
        </div>
      </div>

      {/* Last play */}
      <div className="border-t border-white/5 pt-3">
        {last_scorer && last_scorer !== '—' && (
          <p className="text-xs font-semibold text-electric mb-0.5">{last_scorer}</p>
        )}
        <p className="text-xs text-muted italic leading-snug line-clamp-2">
          {last_play_description || 'Awaiting next play…'}
        </p>
      </div>

      {/* Timestamp */}
      {updated_at && (
        <p className="text-[10px] text-muted/50 text-right">
          Updated {new Date(updated_at).toLocaleTimeString()}
        </p>
      )}
    </div>
  )
}
