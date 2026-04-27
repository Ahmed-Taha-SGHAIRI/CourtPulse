import React from 'react'

const streakStyle = {
  'On Fire':  { color: '#ef4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.25)' },
  'Hot':      { color: '#f97316', bg: 'rgba(249,115,22,0.08)',  border: 'rgba(249,115,22,0.25)' },
  'Lukewarm': { color: '#f0b429', bg: 'rgba(240,180,41,0.06)',  border: 'rgba(240,180,41,0.2)' },
  'Cold':     { color: '#60a5fa', bg: 'rgba(96,165,250,0.07)',  border: 'rgba(96,165,250,0.2)' },
  'Freezing': { color: '#818cf8', bg: 'rgba(129,140,248,0.08)', border: 'rgba(129,140,248,0.25)' },
}

const streakEmoji = {
  'On Fire':  '',
  'Hot':      '',
  'Lukewarm': '',
  'Cold':     '',
  'Freezing': '',
}

export default function StreakCard({ team_name, team_abbr, streak_label, rolling_5game_win_rate }) {
  const style = streakStyle[streak_label] || { color: '#8b9ab5', bg: 'rgba(139,154,181,0.06)', border: 'rgba(139,154,181,0.2)' }
  const pct = rolling_5game_win_rate != null ? (rolling_5game_win_rate * 100).toFixed(1) + '%' : '—'

  return (
    <div
      className="flex flex-col items-center gap-2 p-5 rounded-xl flex-shrink-0"
      style={{
        background: style.bg,
        border: `1px solid ${style.border}`,
        minWidth: '140px',
      }}
    >
      {/* Team abbreviation */}
      <div
        className="stat-number"
        style={{ fontSize: '48px', lineHeight: 1, color: '#e2e8f0', letterSpacing: '-0.02em' }}
      >
        {team_abbr}
      </div>

      {/* Team name */}
      <div className="text-muted text-center" style={{ fontSize: '11px', lineHeight: 1.3 }}>
        {team_name}
      </div>

      {/* Streak badge */}
      <span
        className="badge mt-1"
        style={{ color: style.color, background: `${style.color}18`, border: `1px solid ${style.border}` }}
      >
        {streakEmoji[streak_label]} {streak_label}
      </span>

      {/* Win rate */}
      <div
        className="stat-number"
        style={{ fontSize: '28px', color: style.color, lineHeight: 1 }}
      >
        {pct}
      </div>
      <div className="text-muted" style={{ fontSize: '10px' }}>last 5 games</div>
    </div>
  )
}
