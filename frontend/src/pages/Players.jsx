// frontend/src/pages/Players.jsx
import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, Cell,
} from 'recharts'
import PlayerTable from '../components/PlayerTable.jsx'

const fetcher = (url) => axios.get(url).then(r => r.data)
const STALE = 5 * 60 * 1000

const TIER_COLORS = {
  'Star':        '#f59e0b',
  'Starter':     '#3b82f6',
  'Role Player': '#6b7280',
  'Bench':       '#374151',
}

function ScatterTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  return (
    <div className="glass-card p-2 text-xs">
      <p className="text-ice font-semibold">#{d.player_id}</p>
      <p className="text-muted">{d.team}</p>
      <p>PTS: <span className="text-ice">{d.pts?.toFixed(1)}</span></p>
      <p>AST: <span className="text-ice">{d.ast?.toFixed(1)}</span></p>
      <p>Tier: <span className="text-amber">{d.tier}</span></p>
    </div>
  )
}

function FantasyTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="glass-card p-2 text-xs">
      <p className="text-ice font-semibold">#{d.payload.player_id}</p>
      <p className="text-electric">{d.value?.toFixed(1)} fantasy pts</p>
    </div>
  )
}

export default function Players() {
  const { data: players = [], isLoading } = useQuery({
    queryKey: ['players'],
    queryFn:  () => fetcher('/api/players?limit=200'),
    staleTime: STALE,
  })

  /* Summary chips */
  const tierCounts = useMemo(() => {
    const counts = { Star: 0, Starter: 0, 'Role Player': 0, Bench: 0 }
    players.forEach(p => { if (p.tier in counts) counts[p.tier]++ })
    return counts
  }, [players])

  const avgPer = useMemo(() => {
    if (!players.length) return 0
    const sum = players.reduce((s, p) => s + (p.per ?? 0), 0)
    return (sum / players.length).toFixed(1)
  }, [players])

  /* Top 10 by fantasy score */
  const top10Fantasy = useMemo(() =>
    [...players]
      .sort((a, b) => (b.fantasy_score ?? 0) - (a.fantasy_score ?? 0))
      .slice(0, 10),
    [players]
  )

  /* Scatter data: pts vs ast, coloured by tier */
  const scatterByTier = useMemo(() => {
    const groups = {}
    players.forEach(p => {
      const t = p.tier ?? 'Bench'
      if (!groups[t]) groups[t] = []
      groups[t].push(p)
    })
    return groups
  }, [players])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="glass-card h-12 animate-pulse w-48" />
        <div className="glass-card h-96 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h1 className="font-display text-3xl font-bold text-ice tracking-wide">Player Analytics</h1>
        <p className="text-sm text-muted mt-1">Season averages, efficiency ratings, and fantasy scores</p>
      </div>

      {/* Summary chips */}
      <div className="flex flex-wrap gap-3">
        <div className="glass-card px-4 py-2 flex items-center gap-2">
          <span className="text-muted text-xs uppercase tracking-widest">Total</span>
          <span className="text-xl font-bold font-display text-ice">{players.length}</span>
        </div>
        <div className="glass-card px-4 py-2 flex items-center gap-2">
          <span className="text-muted text-xs uppercase tracking-widest">Avg PER</span>
          <span className="text-xl font-bold font-display text-amber">{avgPer}</span>
        </div>
        {Object.entries(tierCounts).map(([tier, count]) => (
          <div key={tier} className="glass-card px-4 py-2 flex items-center gap-2">
            <span className="text-muted text-xs uppercase tracking-widest">{tier}</span>
            <span className="text-xl font-bold font-display text-ice">{count}</span>
          </div>
        ))}
      </div>

      {/* Full player table */}
      <PlayerTable data={players} />

      {/* Charts row */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* PTS vs AST scatter */}
        <div className="glass-card p-5">
          <h2 className="font-display text-xl font-bold text-ice mb-4">PTS vs AST by Tier</h2>
          <ResponsiveContainer width="100%" height={280}>
            <ScatterChart margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="pts" name="PTS" tick={{ fontSize: 10, fill: '#6b7280' }} label={{ value: 'PTS', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 11 }} />
              <YAxis dataKey="ast" name="AST" tick={{ fontSize: 10, fill: '#6b7280' }} label={{ value: 'AST', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 11 }} />
              <Tooltip content={<ScatterTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#6b7280' }} />
              {Object.entries(scatterByTier).map(([tier, pts]) => (
                <Scatter
                  key={tier}
                  name={tier}
                  data={pts}
                  fill={TIER_COLORS[tier] ?? '#6b7280'}
                  opacity={0.8}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        {/* Top 10 fantasy score bar */}
        <div className="glass-card p-5">
          <h2 className="font-display text-xl font-bold text-ice mb-4">Top 10 — Fantasy Score</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={top10Fantasy}
              layout="vertical"
              margin={{ top: 0, right: 20, left: 30, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis
                type="category"
                dataKey="player_id"
                tick={{ fontSize: 10, fill: '#9ca3af' }}
                tickFormatter={v => `#${v}`}
                width={38}
              />
              <Tooltip content={<FantasyTooltip />} />
              <Bar dataKey="fantasy_score" radius={[0, 4, 4, 0]}>
                {top10Fantasy.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={i === 0 ? '#f59e0b' : i < 3 ? '#3b82f6' : '#6366f1'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
