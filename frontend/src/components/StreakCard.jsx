// frontend/src/components/StreakCard.jsx
import React from 'react'

/**
 * StreakCard — displays a team's hot/cold streak status.
 *
 * Props:
 *   team             {string}
 *   streak_label     {string} — 'On Fire'|'Hot'|'Lukewarm'|'Cold'|'Freezing'
 *   rolling_win_rate {number} — 0.0 – 1.0
 *   window_games     {number}
 */

const LABEL_META = {
  'On Fire':  { emoji: '🔥', color: '#f97316', glow: 'rgba(249,115,22,0.3)',  textCls: 'streak-on-fire'  },
  'Hot':      { emoji: '☀️', color: '#f59e0b', glow: 'rgba(245,158,11,0.3)',  textCls: 'streak-hot'      },
  'Lukewarm': { emoji: '🏀', color: '#a3a3a3', glow: 'rgba(163,163,163,0.2)', textCls: 'streak-lukewarm' },
  'Cold':     { emoji: '❄️', color: '#60a5fa', glow: 'rgba(96,165,250,0.3)',  textCls: 'streak-cold'     },
  'Freezing': { emoji: '🥶', color: '#bfdbfe', glow: 'rgba(191,219,254,0.3)', textCls: 'streak-freezing' },
}

/** SVG circular progress ring */
function RingProgress({ rate = 0, color = '#3b82f6', size = 64 }) {
  const r = (size - 8) / 2
  const circumference = 2 * Math.PI * r
  const offset = circumference * (1 - Math.min(1, Math.max(0, rate)))

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      {/* Track */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={6}
      />
      {/* Fill */}
      <circle
        cx={size / 2} cy={size / 2} r={r}
        fill="none" stroke={color} strokeWidth={6}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.8s ease' }}
      />
    </svg>
  )
}

export default function StreakCard({ team, streak_label, rolling_win_rate, window_games }) {
  const meta = LABEL_META[streak_label] ?? LABEL_META['Lukewarm']
  const pct = Math.round((rolling_win_rate ?? 0) * 100)

  return (
    <div
      className="glass-card p-4 flex flex-col gap-3 min-w-[180px] max-w-[220px] flex-shrink-0"
      style={{
        borderColor: `${meta.color}30`,
        boxShadow: `0 4px 24px ${meta.glow}`,
      }}
    >
      {/* Emoji + label */}
      <div className="flex items-center gap-2">
        <span className="text-2xl" aria-hidden="true">{meta.emoji}</span>
        <span className={`text-sm font-bold ${meta.textCls}`}>{streak_label}</span>
      </div>

      {/* Team name */}
      <p
        className="font-extrabold text-ice text-sm leading-tight truncate"
        style={{ fontFamily: '"Barlow Condensed", sans-serif' }}
        title={team}
      >
        {team ?? '—'}
      </p>

      {/* Ring + percentage */}
      <div className="flex items-center gap-3">
        <div className="relative">
          <RingProgress rate={rolling_win_rate ?? 0} color={meta.color} size={56} />
          <span
            className="absolute inset-0 flex items-center justify-center text-xs font-bold"
            style={{ color: meta.color }}
          >
            {pct}%
          </span>
        </div>
        <div className="text-xs text-muted">
          <p className="font-semibold text-ice">{pct}% win rate</p>
          <p>Last {window_games ?? 5} games</p>
        </div>
      </div>
    </div>
  )
}
