import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { getKpis, getStandings } from '../api/client'
import KpiCard from '../components/KpiCard'
import StandingsTable from '../components/StandingsTable'

const CONFERENCES = ['Eastern', 'Western']

function CustomTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  return (
    <div
      className="card px-4 py-3"
      style={{ fontSize: '13px', minWidth: '180px' }}
    >
      <div className="font-bold text-white mb-1">{d.team_name}</div>
      <div className="text-muted">
        Win%: <span className="text-electric font-semibold">{(d.win_pct * 100).toFixed(1)}%</span>
      </div>
      <div className="text-muted">
        Record:{' '}
        <span className="text-white">{d.wins}–{d.losses}</span>
      </div>
    </div>
  )
}

export default function Overview() {
  const [conference, setConference] = useState(null)

  const { data: kpis } = useQuery({
    queryKey: ['kpis'],
    queryFn: () => getKpis().then((r) => r.data),
  })

  const { data: standings, isLoading } = useQuery({
    queryKey: ['standings', conference],
    queryFn: () => getStandings(conference).then((r) => r.data),
  })

  const topTeams = (standings || [])
    .slice()
    .sort((a, b) => (b.win_pct ?? 0) - (a.win_pct ?? 0))
    .slice(0, 10)

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col gap-8">
      <div>
        <h1 className="font-display font-bold text-white" style={{ fontSize: '32px' }}>
          League Overview
        </h1>
        <p className="text-muted mt-1" style={{ fontSize: '14px' }}>
          2024 NBA Season — standings, efficiency, and key metrics
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          icon=""
          title="Best Team"
          value={kpis?.best_team?.team_name ?? '—'}
          subtitle={
            kpis?.best_team?.wins != null
              ? `${kpis.best_team.wins} wins · ${(kpis.best_team.win_pct * 100).toFixed(1)}% WR`
              : 'No data yet'
          }
        />
        <KpiCard
          icon=""
          title="Top Scorer"
          value={kpis?.top_scorer?.player_name ?? '—'}
          subtitle={
            kpis?.top_scorer?.pts != null
              ? `${kpis.top_scorer.pts.toFixed(1)} PPG · ${kpis.top_scorer.team_abbreviation}`
              : 'No data yet'
          }
        />
        <KpiCard
          icon=""
          title="Avg PPG"
          value={kpis?.avg_ppg != null ? kpis.avg_ppg.toFixed(1) : '—'}
          subtitle="League average points per game"
        />
        <KpiCard
          icon=""
          title="Total Teams"
          value={kpis?.total_teams ?? '—'}
          subtitle="Active NBA franchises"
        />
      </div>

      {/* Conference Tabs + Table */}
      <div className="card overflow-hidden">
        <div
          className="flex items-center gap-1 px-4 pt-4 pb-0"
          style={{ borderBottom: '1px solid rgba(79,142,247,0.1)' }}
        >
          <button
            id="tab-all"
            onClick={() => setConference(null)}
            className="px-4 py-2 text-sm font-semibold rounded-t-lg transition-colors"
            style={
              conference === null
                ? { color: '#4f8ef7', borderBottom: '2px solid #4f8ef7', background: 'transparent' }
                : { color: '#8b9ab5', borderBottom: '2px solid transparent', background: 'transparent' }
            }
          >
            All
          </button>
          {CONFERENCES.map((c) => (
            <button
              key={c}
              id={`tab-${c.toLowerCase()}`}
              onClick={() => setConference(c)}
              className="px-4 py-2 text-sm font-semibold rounded-t-lg transition-colors"
              style={
                conference === c
                  ? { color: '#4f8ef7', borderBottom: '2px solid #4f8ef7', background: 'transparent' }
                  : { color: '#8b9ab5', borderBottom: '2px solid transparent', background: 'transparent' }
              }
            >
              {c} Conference
            </button>
          ))}
        </div>

        <div className="p-4">
          {isLoading ? (
            <div className="text-muted text-center py-10">Loading standings…</div>
          ) : (
            <StandingsTable data={standings || []} />
          )}
        </div>
      </div>

      {/* Win % Bar Chart */}
      {topTeams.length > 0 && (
        <div className="card p-6">
          <h2 className="font-display font-bold text-white mb-4" style={{ fontSize: '20px' }}>
            Top 10 Teams by Win %
          </h2>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={topTeams} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <XAxis
                dataKey="team_abbreviation"
                tick={{ fill: '#8b9ab5', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: '#8b9ab5', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(79,142,247,0.06)' }} />
              <Bar dataKey="win_pct" radius={[4, 4, 0, 0]}>
                {topTeams.map((_, i) => (
                  <Cell key={i} fill="#4f8ef7" opacity={1 - i * 0.06} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
