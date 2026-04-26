// frontend/src/components/PlayerTable.jsx
import React, { useState, useMemo } from 'react'

/**
 * PlayerTable — searchable, filterable, sortable player efficiency table.
 *
 * Props:
 *   data {array} — rows from /api/players
 */

const TIERS = ['All', 'Star', 'Starter', 'Role Player', 'Bench']

const COLUMNS = [
  { key: 'overall_rank', label: '#',             numeric: true  },
  { key: 'player_id',    label: 'Player ID',     numeric: true  },
  { key: 'team',         label: 'Team',          numeric: false },
  { key: 'pts',          label: 'PTS',           numeric: true  },
  { key: 'reb',          label: 'REB',           numeric: true  },
  { key: 'ast',          label: 'AST',           numeric: true  },
  { key: 'stl',          label: 'STL',           numeric: true  },
  { key: 'blk',          label: 'BLK',           numeric: true  },
  { key: 'per',          label: 'PER',           numeric: true  },
  { key: 'fantasy_score', label: 'Fantasy',      numeric: true  },
  { key: 'tier',         label: 'Tier',          numeric: false },
]

function TierBadge({ tier }) {
  const cls = {
    'Star':        'tier-star',
    'Starter':     'tier-starter',
    'Role Player': 'tier-role',
    'Bench':       'tier-bench',
  }[tier] ?? 'tier-bench'
  return <span className={`pill ${cls}`}>{tier ?? '—'}</span>
}

export default function PlayerTable({ data = [] }) {
  const [search, setSearch]     = useState('')
  const [tier, setTier]         = useState('All')
  const [sortKey, setSortKey]   = useState('per')
  const [sortDir, setSortDir]   = useState(-1)

  const filtered = useMemo(() => {
    let rows = data
    if (tier !== 'All') rows = rows.filter(r => r.tier === tier)
    if (search.trim()) {
      const q = search.toLowerCase()
      rows = rows.filter(r =>
        String(r.player_id ?? '').includes(q) ||
        (r.team ?? '').toLowerCase().includes(q)
      )
    }
    return [...rows].sort((a, b) => {
      const av = a[sortKey] ?? ''
      const bv = b[sortKey] ?? ''
      if (typeof av === 'number') return sortDir * (av - bv)
      return sortDir * String(av).localeCompare(String(bv))
    })
  }, [data, tier, search, sortKey, sortDir])

  const handleSort = (key) => {
    if (key === sortKey) setSortDir(d => -d)
    else { setSortKey(key); setSortDir(-1) }
  }

  return (
    <div className="glass-card overflow-hidden">
      {/* Toolbar */}
      <div className="px-5 py-4 flex flex-wrap gap-3 items-center border-b border-white/5">
        {/* Search */}
        <input
          type="search"
          placeholder="Search by team or ID…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-navy border border-white/10 rounded-lg px-3 py-1.5 text-sm text-ice placeholder-muted outline-none focus:border-electric transition-colors w-48"
          id="player-search"
        />

        {/* Tier filter pills */}
        <div className="flex gap-2 flex-wrap">
          {TIERS.map(t => (
            <button
              key={t}
              onClick={() => setTier(t)}
              id={`tier-filter-${t.toLowerCase().replace(' ', '-')}`}
              className={`pill cursor-pointer border transition-all text-xs ${
                tier === t
                  ? 'border-electric bg-electric/20 text-ice'
                  : 'border-white/10 bg-white/5 text-muted hover:border-electric/50 hover:text-ice'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <span className="ml-auto text-xs text-muted">{filtered.length} players</span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
        <table className="data-table">
          <thead className="sticky top-0 z-10">
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
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length} className="text-center text-muted py-10">
                  No players match your filters
                </td>
              </tr>
            ) : filtered.map((row, i) => (
              <tr key={`${row.player_id}-${i}`}>
                <td className="text-muted font-mono text-xs">{row.overall_rank ?? i + 1}</td>
                <td className="text-electric font-mono text-xs">#{row.player_id ?? '—'}</td>
                <td className="font-semibold text-ice whitespace-nowrap">{row.team ?? '—'}</td>
                <td className="text-ice font-bold">{row.pts?.toFixed(1) ?? '—'}</td>
                <td>{row.reb?.toFixed(1) ?? '—'}</td>
                <td>{row.ast?.toFixed(1) ?? '—'}</td>
                <td>{row.stl?.toFixed(1) ?? '—'}</td>
                <td>{row.blk?.toFixed(1) ?? '—'}</td>
                <td className="font-semibold text-amber">{row.per?.toFixed(1) ?? '—'}</td>
                <td className="text-electric font-mono text-xs">{row.fantasy_score?.toFixed(1) ?? '—'}</td>
                <td><TierBadge tier={row.tier} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
