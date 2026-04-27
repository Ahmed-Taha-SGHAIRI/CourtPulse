import React from 'react'

function isLive(status) {
  if (!status) return false
  const s = status.toLowerCase()
  return !s.includes('final') && !s.includes('no_game')
}

export default function LiveScoreCard({ game }) {
  const live = isLive(game.status)

  return (
    <div
      className="card p-5 flex flex-col gap-3"
      style={live ? { borderColor: 'rgba(34,197,94,0.35)' } : {}}
    >
      {/* Status bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {live && (
            <span className="w-2 h-2 rounded-full bg-win animate-pulse inline-block" />
          )}
          <span
            className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: live ? '#22c55e' : '#8b9ab5' }}
          >
            {game.status || '—'}
          </span>
        </div>
        <span className="text-muted" style={{ fontSize: '12px' }}>
          {game.game_date}
        </span>
      </div>

      {/* Scores */}
      <div className="flex items-center justify-between gap-4">
        {/* Home */}
        <div className="flex flex-col items-start gap-0.5 flex-1">
          <span className="text-white font-semibold" style={{ fontSize: '14px' }}>
            {game.home_team}
          </span>
          <span className="text-muted" style={{ fontSize: '11px' }}>
            {game.home_team_abbr}
          </span>
        </div>

        {/* Score */}
        <div className="flex items-center gap-3">
          <span className="stat-number text-white" style={{ fontSize: '36px' }}>
            {game.home_score ?? 0}
          </span>
          <span className="text-muted stat-number" style={{ fontSize: '20px' }}>—</span>
          <span className="stat-number text-white" style={{ fontSize: '36px' }}>
            {game.visitor_score ?? 0}
          </span>
        </div>

        {/* Visitor */}
        <div className="flex flex-col items-end gap-0.5 flex-1">
          <span className="text-white font-semibold" style={{ fontSize: '14px' }}>
            {game.visitor_team}
          </span>
          <span className="text-muted" style={{ fontSize: '11px' }}>
            {game.visitor_team_abbr}
          </span>
        </div>
      </div>

      {/* Period / Clock */}
      <div className="flex items-center justify-center gap-3 text-muted" style={{ fontSize: '12px' }}>
        {game.period ? <span>Q{game.period}</span> : null}
        {game.clock ? <span>{game.clock}</span> : null}
      </div>
    </div>
  )
}
