// frontend/src/pages/Overview.jsx
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts'
import KpiCard from '../components/KpiCard.jsx'
import StandingsTable from '../components/StandingsTable.jsx'

const fetcher = (url) => axios.get(url).then(r => r.data)

const STALE = 5 * 60 * 1000 // 5 minutes

/* Custom tooltip for the win% bar chart */
function WinPctTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div className="glass-card p-2 text-xs">
      <p className="text-ice font-semibold">{d.payload.team}</p>
      <p className="text-electric">{(d.value * 100).toFixed(1)}% wins</p>
    </div>
  )
}

export default function Overview() {
  const { data: kpis, isLoading: kLoad } = useQuery({
    queryKey: ['kpis'],
    queryFn:  () => fetcher('/api/kpis'),
    staleTime: STALE,
  })

  const { data: standings = [], isLoading: sLoad } = useQuery({
    queryKey: ['standings'],
    queryFn:  () => fetcher('/api/standings'),
    staleTime: STALE,
  })

  /* Top 10 teams by win_pct for bar chart */
  const chartData = [...standings]
    .sort((a, b) => (b.win_pct ?? 0) - (a.win_pct ?? 0))
    .slice(0, 10)
    .map(t => ({ team: t.team?.split(' ').pop() ?? '?', win_pct: t.win_pct ?? 0 }))

  const loading = kLoad || sLoad

  return (
    <div className="space-y-6">
      {/* Page title */}
      <div>
        <h1 className="font-display text-3xl font-bold text-ice tracking-wide">
          League Overview
        </h1>
        <p className="text-sm text-muted mt-1">
          Season standings, key metrics, and top-10 win rates
        </p>
      </div>

      {/* ── KPI Cards ─────────────────────────────────────────────────── */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card h-28 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            title="Best Team"
            value={kpis?.best_team ?? '—'}
            subtitle="Highest win percentage"
            icon="🏆"
          />
          <KpiCard
            title="Top Scorer"
            value={kpis?.top_scorer ?? '—'}
            subtitle="Season average PPG leader"
            icon="🔥"
          />
          <KpiCard
            title="Avg PPG"
            value={kpis?.avg_points_per_game ?? 0}
            subtitle="League-wide average points per game"
            icon="📊"
            trend="up"
          />
          <KpiCard
            title="Games Played"
            value={kpis?.total_games_played ?? 0}
            subtitle="Completed games this season"
            icon="📅"
          />
        </div>
      )}

      {/* ── Standings Tables ──────────────────────────────────────────── */}
      {sLoad ? (
        <div className="glass-card h-64 animate-pulse" />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <StandingsTable
            data={standings.filter((_, i) => i % 2 === 0)} // simplified split
            conference="Eastern Conference"
          />
          <StandingsTable
            data={standings.filter((_, i) => i % 2 !== 0)}
            conference="Western Conference"
          />
        </div>
      )}

      {/* ── Win% Bar Chart ────────────────────────────────────────────── */}
      {chartData.length > 0 && (
        <div className="glass-card p-5">
          <h2 className="font-display text-xl font-bold text-ice mb-4">
            Top 10 Teams by Win %
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="team" tick={{ fontSize: 11, fill: '#6b7280' }} />
              <YAxis
                tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 11, fill: '#6b7280' }}
                domain={[0, 1]}
              />
              <Tooltip content={<WinPctTooltip />} />
              <Bar dataKey="win_pct" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={i === 0 ? '#10b981' : i < 3 ? '#3b82f6' : '#6366f1'}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
