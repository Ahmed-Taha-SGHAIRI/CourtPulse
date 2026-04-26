// frontend/src/components/StandingsTable.jsx
import React, { useState } from 'react'

/**
 * StandingsTable — sortable, color-coded team standings table.
 *
 * Props:
 *   data       {array}  — standing rows from /api/standings
 *   conference {string} — display label (e.g. "Eastern Conference")
 */

const COLUMNS = [
  { key: 'overall_seed', label: '#',           numeric: true  },
  { key: 'team',         label: 'Team',         numeric: false },
  { key: 'wins',         label: 'W',            numeric: true  },
  { key: 'losses',       label: 'L',            numeric: true  },
  { key: 'win_pct',      label: 'WIN%',         numeric: true  },
  { key: 'home_record',  label: 'Home',         numeric: false },
  { key: 'away_record',  label: 'Away',         numeric: false },
  { key: 'avg_pts_scored', label: 'PPG',        numeric: true  },
  { key: 'avg_point_diff', label: '+/-',        numeric: true  },
  { key: 'current_streak', label: 'Streak',     numeric: true  },
  { key: 'playoff_position', label: 'Status',   numeric: false },
]

function StreakBadge({ value }) {
  if (!value && value !== 0) return <span className="text-muted">—</span>
  const v = Number(value)
  if (v > 0) return (
    <span className="pill" style={{ background: 'rgba(16,185,129,0.2)', color: '#10b981' }}>
      W{v}
    </span>
  )
  if (v < 0) return (
    <span className="pill" style={{ background: 'rgba(239,68,68,0.2)', color: '#ef4444' }}>
      L{Math.abs(v)}
    </span>
  )
  return <span className="text-muted">—</span>
}

function WinPctBar({ pct }) {
  const p = Math.min(1, Math.max(0, Number(pct) || 0))
  return (
    <div className="flex items-center gap-2">
      <span className="text-ice text-xs w-8">{(p * 100).toFixed(1)}</span>
      <div className="progress-bar-track">
        <div className="progress-bar-fill" style={{ width: `${p * 100}%` }} />
      </div>
    </div>
  )
}

function RowBorder({ position }) {
  if (position <= 6)  return 'border-l-2 border-emerald'
  if (position <= 10) return 'border-l-2 border-amber'
  return 'border-l-2 border-transparent'
}

export default function StandingsTable({ data = [], conference = '' }) {
  const [sortKey, setSortKey] = useState('win_pct')
  const [sortDir, setSortDir] = useState(-1) // -1 = desc

  const handleSort = (key) => {
    if (key === sortKey) setSortDir(d => -d)
    else { setSortKey(key); setSortDir(-1) }
  }

  const sorted = [...data].sort((a, b) => {
    const av = a[sortKey] ?? ''
    const bv = b[sortKey] ?? ''
    if (typeof av === 'number') return sortDir * (av - bv)
    return sortDir * String(av).localeCompare(String(bv))
  })

  return (
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="px-5 py-3 border-b border-white/5">
        <h2 className="font-display text-lg font-bold text-ice tracking-wide">
          {conference || 'Standings'}
        </h2>
      </div>

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              {COLUMNS.map(col => (
                <th key={col.key} onClick={() => handleSort(col.key)}>
                  {col.label}
                  {sortKey === col.key && (
                    <span className="ml-1 text-electric">{sortDir === -1 ? '↓' : '↑'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length} className="text-center text-muted py-8">
                  No data yet — run the pipeline first
                </td>
              </tr>
            ) : sorted.map((row, i) => {
              const seed = row.overall_seed ?? i + 1
              return (
                <tr key={row.team ?? i} className={RowBorder({ position: seed })}>
                  <td className="text-muted font-mono text-xs">{seed}</td>
                  <td className="font-semibold text-ice whitespace-nowrap">{row.team ?? '—'}</td>
                  <td className="text-emerald font-bold">{row.wins ?? 0}</td>
                  <td className="text-danger">{row.losses ?? 0}</td>
                  <td><WinPctBar pct={row.win_pct} /></td>
                  <td className="text-muted text-xs">{row.home_record ?? '—'}</td>
                  <td className="text-muted text-xs">{row.away_record ?? '—'}</td>
                  <td>{row.avg_pts_scored ?? '—'}</td>
                  <td className={Number(row.avg_point_diff) >= 0 ? 'text-emerald' : 'text-danger'}>
                    {row.avg_point_diff ? (Number(row.avg_point_diff) >= 0 ? '+' : '') + row.avg_point_diff : '—'}
                  </td>
                  <td><StreakBadge value={row.current_streak} /></td>
                  <td>
                    <span className={`pill text-xs ${
                      row.playoff_position === 'Playoff'    ? 'bg-emerald/20 text-emerald' :
                      row.playoff_position === 'Play-In'   ? 'bg-amber/20 text-amber' :
                                                              'bg-white/5 text-muted'
                    }`}>
                      {row.playoff_position ?? '—'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="px-5 py-2 flex gap-4 border-t border-white/5">
        <span className="flex items-center gap-1.5 text-xs text-muted">
          <span className="w-2 h-2 rounded-full bg-emerald inline-block" />Playoff
        </span>
        <span className="flex items-center gap-1.5 text-xs text-muted">
          <span className="w-2 h-2 rounded-full bg-amber inline-block" />Play-In
        </span>
        <span className="flex items-center gap-1.5 text-xs text-muted">
          <span className="w-2 h-2 rounded-full bg-muted/40 inline-block" />Eliminated
        </span>
      </div>
    </div>
  )
}
