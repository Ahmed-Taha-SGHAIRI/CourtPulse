// frontend/src/pages/Streaks.jsx
import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import StreakCard from '../components/StreakCard.jsx'

const fetcher = (url) => axios.get(url).then(r => r.data)

const HOT_LABELS  = new Set(['On Fire', 'Hot'])
const COLD_LABELS = new Set(['Cold', 'Freezing'])

const LINE_COLORS = ['#f59e0b', '#3b82f6', '#10b981', '#a855f7', '#ef4444']

function LineTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card p-2 text-xs space-y-1">
      <p className="text-muted mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: {(p.value * 100).toFixed(0)}%
        </p>
      ))}
    </div>
  )
}

export default function Streaks() {
  const { data: streaks = [], isLoading } = useQuery({
    queryKey: ['streaks'],
    queryFn:  () => fetcher('/api/streaks'),
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
  })

  const hotTeams  = useMemo(() => streaks.filter(s => HOT_LABELS.has(s.streak_label)),  [streaks])
  const coldTeams = useMemo(() => streaks.filter(s => COLD_LABELS.has(s.streak_label)), [streaks])

  /* Build fake time-series for the top 5 teams (demo since we only have latest snapshot) */
  const top5 = useMemo(() => streaks.slice(0, 5), [streaks])
  const chartData = useMemo(() => {
    // Simulate last 10 game snapshots with slight variance for visualisation
    return Array.from({ length: 10 }, (_, i) => {
      const point = { game: `G-${i + 1}` }
      top5.forEach(t => {
        const base = t.rolling_win_rate ?? 0.5
        const jitter = (Math.random() - 0.5) * 0.25
        point[t.team] = Math.min(1, Math.max(0, parseFloat((base + jitter).toFixed(2))))
      })
      return point
    })
  }, [top5])

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="glass-card h-12 animate-pulse w-48" />
        <div className="glass-card h-40 animate-pulse" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Title */}
      <div>
        <h1 className="font-display text-3xl font-bold text-ice tracking-wide">
          Streak Detector
        </h1>
        <p className="text-sm text-muted mt-1">
          5-game rolling win rate — who's heating up and who's cooling down
        </p>
      </div>

      {/* ── Hot section ────────────────────────────────────────────────── */}
      <section>
        <h2 className="font-display text-2xl font-bold mb-3" style={{ color: '#f97316' }}>
          🔥 On Fire
        </h2>
        {hotTeams.length === 0 ? (
          <p className="text-muted text-sm">No teams currently on a hot streak.</p>
        ) : (
          <div className="flex gap-4 overflow-x-auto pb-2">
            {hotTeams.map(team => (
              <StreakCard key={team.team} {...team} />
            ))}
          </div>
        )}
      </section>

      {/* ── Rolling win rate chart ─────────────────────────────────────── */}
      {top5.length > 0 && (
        <div className="glass-card p-5">
          <h2 className="font-display text-xl font-bold text-ice mb-4">
            Rolling Win Rate — Top 5 Teams
          </h2>
          <p className="text-xs text-muted mb-4">
            Trend over last 10 game windows (simulated variance for illustration)
          </p>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={chartData} margin={{ top: 0, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="game" tick={{ fontSize: 10, fill: '#6b7280' }} />
              <YAxis
                tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                tick={{ fontSize: 10, fill: '#6b7280' }}
                domain={[0, 1]}
              />
              <Tooltip content={<LineTooltip />} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
              {top5.map((team, i) => (
                <Line
                  key={team.team}
                  type="monotone"
                  dataKey={team.team}
                  stroke={LINE_COLORS[i]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Cold section ───────────────────────────────────────────────── */}
      <section>
        <h2 className="font-display text-2xl font-bold mb-3" style={{ color: '#60a5fa' }}>
          🥶 Cold Spells
        </h2>
        {coldTeams.length === 0 ? (
          <p className="text-muted text-sm">No teams currently on a cold streak.</p>
        ) : (
          <div className="flex gap-4 overflow-x-auto pb-2">
            {coldTeams.map(team => (
              <StreakCard key={team.team} {...team} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
