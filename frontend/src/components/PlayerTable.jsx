import React, { useState, useMemo } from 'react'

const TIERS = ['All', 'Star', 'Starter', 'Role Player', 'Bench']

const tierStyle = {
  Star:         { color: '#f0b429', background: 'rgba(240,180,41,0.12)',  border: '1px solid rgba(240,180,41,0.3)' },
  Starter:      { color: '#4f8ef7', background: 'rgba(79,142,247,0.12)', border: '1px solid rgba(79,142,247,0.3)' },
  'Role Player':{ color: '#94a3b8', background: 'rgba(148,163,184,0.1)', border: '1px solid rgba(148,163,184,0.2)' },
  Bench:        { color: '#64748b', background: 'rgba(100,116,139,0.1)', border: '1px solid rgba(100,116,139,0.2)' },
}

function TierBadge({ tier }) {
  const style = tierStyle[tier] || {}
  return (
    <span className="badge" style={style}>
      {tier}
    </span>
  )
}

export default function PlayerTable({ data }) {
  const [search, setSearch] = useState('')
  const [tierFilter, setTierFilter] = useState('All')
  const [sortCol, setSortCol] = useState('per')
  const [sortDir, setSortDir] = useState('desc')

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortCol(col)
      setSortDir('desc')
    }
  }

  const filtered = useMemo(() => {
    let rows = data || []
    if (search) {
      const q = search.toLowerCase()
      rows = rows.filter((r) => (r.player_name || '').toLowerCase().includes(q))
    }
    if (tierFilter !== 'All') {
      rows = rows.filter((r) => r.tier === tierFilter)
    }
    rows = [...rows].sort((a, b) => {
      const av = a[sortCol] ?? 0
      const bv = b[sortCol] ?? 0
      return sortDir === 'asc' ? av - bv : bv - av
    })
    return rows
  }, [data, search, tierFilter, sortCol, sortDir])

  const SortHeader = ({ col, label }) => (
    <th
      className="cursor-pointer select-none hover:text-white transition-colors"
      onClick={() => handleSort(col)}
    >
      {label}
      {sortCol === col && (
        <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
      )}
    </th>
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-center">
        <input
          type="text"
          placeholder="Search player..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-4 py-2 rounded-lg text-sm text-white placeholder-muted outline-none focus:ring-1 focus:ring-electric"
          style={{ background: '#0f1729', border: '1px solid rgba(79,142,247,0.2)', minWidth: '200px' }}
          id="player-search-input"
        />
        <div className="flex gap-2">
          {TIERS.map((t) => (
            <button
              key={t}
              id={`tier-filter-${t.replace(' ', '-')}`}
              onClick={() => setTierFilter(t)}
              className="px-3 py-1 rounded-full text-xs font-semibold transition-all"
              style={
                tierFilter === t
                  ? { background: '#4f8ef7', color: '#fff' }
                  : { background: '#0f1729', color: '#8b9ab5', border: '1px solid rgba(79,142,247,0.2)' }
              }
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl" style={{ border: '1px solid rgba(79,142,247,0.12)' }}>
        <table className="cp-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Player</th>
              <th>Team</th>
              <th>Pos</th>
              <SortHeader col="pts" label="PTS" />
              <SortHeader col="reb" label="REB" />
              <SortHeader col="ast" label="AST" />
              <SortHeader col="per" label="PER" />
              <SortHeader col="fantasy_score" label="Fantasy" />
              <th>Tier</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={10} className="text-center text-muted py-8">
                  No players found.
                </td>
              </tr>
            ) : (
              filtered.map((p, i) => (
                <tr key={p.player_id ?? i}>
                  <td className="text-muted stat-number" style={{ fontSize: '15px' }}>
                    {i + 1}
                  </td>
                  <td className="font-semibold text-white">{p.player_name}</td>
                  <td className="text-muted">{p.team_abbreviation}</td>
                  <td className="text-muted">{p.position || '—'}</td>
                  <td className="stat-number" style={{ color: '#4f8ef7', fontSize: '15px' }}>
                    {p.pts?.toFixed(1) ?? '—'}
                  </td>
                  <td className="stat-number" style={{ fontSize: '15px' }}>
                    {p.reb?.toFixed(1) ?? '—'}
                  </td>
                  <td className="stat-number" style={{ fontSize: '15px' }}>
                    {p.ast?.toFixed(1) ?? '—'}
                  </td>
                  <td className="stat-number font-bold" style={{ color: '#f0b429', fontSize: '15px' }}>
                    {p.per?.toFixed(2) ?? '—'}
                  </td>
                  <td className="stat-number" style={{ fontSize: '15px' }}>
                    {p.fantasy_score?.toFixed(1) ?? '—'}
                  </td>
                  <td>
                    <TierBadge tier={p.tier} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
