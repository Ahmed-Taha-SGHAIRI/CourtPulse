import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ZAxis,
} from 'recharts'
import { getPlayers } from '../api/client'
import PlayerTable from '../components/PlayerTable'

const tierColor = {
  Star:          '#f0b429',
  Starter:       '#4f8ef7',
  'Role Player': '#94a3b8',
  Bench:         '#475569',
}

function ScatterTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  return (
    <div className="card px-4 py-3" style={{ fontSize: '13px' }}>
      <div className="font-bold text-white">{d.player_name}</div>
      <div className="text-muted">{d.team_abbreviation} · {d.tier}</div>
      <div className="text-muted mt-1">
        PTS <span className="text-electric">{d.pts?.toFixed(1)}</span> ·{' '}
        AST <span className="text-electric">{d.ast?.toFixed(1)}</span> ·{' '}
        PER <span className="text-gold">{d.per?.toFixed(2)}</span>
      </div>
    </div>
  )
}

export default function Players() {
  const { data: players, isLoading } = useQuery({
    queryKey: ['players'],
    queryFn: () => getPlayers({ limit: 200 }).then((r) => r.data),
  })

  const rows = players || []

  const tierCounts = useMemo(() => {
    const counts = { Star: 0, Starter: 0, 'Role Player': 0, Bench: 0 }
    rows.forEach((p) => {
      if (counts[p.tier] !== undefined) counts[p.tier]++
    })
    return counts
  }, [rows])

  const avgPer = useMemo(() => {
    if (!rows.length) return 0
    return (rows.reduce((s, p) => s + (p.per ?? 0), 0) / rows.length).toFixed(2)
  }, [rows])

  // Group by tier for scatter chart
  const byTier = useMemo(() => {
    const map = {}
    rows.forEach((p) => {
      if (!map[p.tier]) map[p.tier] = []
      map[p.tier].push(p)
    })
    return map
  }, [rows])

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col gap-8">
      <div>
        <h1 className="font-display font-bold text-white" style={{ fontSize: '32px' }}>
          Player Efficiency
        </h1>
        <p className="text-muted mt-1" style={{ fontSize: '14px' }}>
          2024 season averages · PER rankings · fantasy scores
        </p>
      </div>

      {/* Summary chips */}
      <div className="flex flex-wrap gap-3">
        <div className="card px-4 py-2 flex items-center gap-2">
          <span className="text-muted text-xs uppercase tracking-widest">Players</span>
          <span className="stat-number text-white" style={{ fontSize: '20px' }}>{rows.length}</span>
        </div>
        <div className="card px-4 py-2 flex items-center gap-2">
          <span className="text-muted text-xs uppercase tracking-widest">Avg PER</span>
          <span className="stat-number text-gold" style={{ fontSize: '20px' }}>{avgPer}</span>
        </div>
        {Object.entries(tierCounts).map(([tier, count]) => (
          <div
            key={tier}
            className="px-4 py-2 flex items-center gap-2 rounded-xl"
            style={{
              background: `${tierColor[tier]}12`,
              border: `1px solid ${tierColor[tier]}30`,
            }}
          >
            <span style={{ color: tierColor[tier], fontSize: '12px', fontWeight: 600 }}>{tier}</span>
            <span className="stat-number text-white" style={{ fontSize: '18px' }}>{count}</span>
          </div>
        ))}
      </div>

      {/* Player Table */}
      {isLoading ? (
        <div className="text-muted text-center py-10">Loading players…</div>
      ) : (
        <PlayerTable data={rows} />
      )}

      {/* Scatter Chart */}
      {rows.length > 0 && (
        <div className="card p-6">
          <h2 className="font-display font-bold text-white mb-4" style={{ fontSize: '20px' }}>
            Points vs Assists (by Tier)
          </h2>
          <ResponsiveContainer width="100%" height={320}>
            <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: -10 }}>
              <XAxis
                dataKey="pts"
                name="PTS"
                tick={{ fill: '#8b9ab5', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                label={{ value: 'Points', position: 'insideBottomRight', fill: '#8b9ab5', fontSize: 12, dy: 10 }}
              />
              <YAxis
                dataKey="ast"
                name="AST"
                tick={{ fill: '#8b9ab5', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                label={{ value: 'Assists', angle: -90, position: 'insideLeft', fill: '#8b9ab5', fontSize: 12 }}
              />
              <ZAxis range={[40, 40]} />
              <Tooltip content={<ScatterTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#8b9ab5' }} />
              {Object.entries(byTier).map(([tier, data]) => (
                <Scatter
                  key={tier}
                  name={tier}
                  data={data}
                  fill={tierColor[tier] || '#8b9ab5'}
                  fillOpacity={0.75}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-4 mt-3 justify-center">
            {Object.entries(tierColor).map(([tier, color]) => (
              <div key={tier} className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full inline-block" style={{ background: color }} />
                <span className="text-muted" style={{ fontSize: '12px' }}>{tier}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
