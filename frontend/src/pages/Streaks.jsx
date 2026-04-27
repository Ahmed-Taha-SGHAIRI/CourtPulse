import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { getStreaks } from '../api/client'
import StreakCard from '../components/StreakCard'

const HOT_LABELS  = new Set(['On Fire', 'Hot'])
const COLD_LABELS = new Set(['Cold', 'Freezing'])

function barColor(rate) {
  if (rate >= 0.6) return '#22c55e'
  if (rate >= 0.4) return '#f0b429'
  return '#ef4444'
}

function BarTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null
  const d = payload[0].payload
  return (
    <div className="card px-4 py-3" style={{ fontSize: '13px' }}>
      <div className="font-bold text-white">{d.team_name || d.team_abbr}</div>
      <div className="text-muted">
        Win rate:{' '}
        <span style={{ color: barColor(d.rolling_5game_win_rate) }}>
          {(d.rolling_5game_win_rate * 100).toFixed(1)}%
        </span>
      </div>
      <div className="text-muted">{d.streak_label}</div>
    </div>
  )
}

export default function Streaks() {
  const { data: streaks, isLoading } = useQuery({
    queryKey: ['streaks'],
    queryFn: () => getStreaks().then((r) => r.data),
  })

  const rows = streaks || []
  const hotTeams  = useMemo(() => rows.filter((r) => HOT_LABELS.has(r.streak_label)),  [rows])
  const coldTeams = useMemo(() => rows.filter((r) => COLD_LABELS.has(r.streak_label)), [rows])

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col gap-10">
      <div>
        <h1 className="font-display font-bold text-white" style={{ fontSize: '32px' }}>
          Hot &amp; Cold Streaks
        </h1>
        <p className="text-muted mt-1" style={{ fontSize: '14px' }}>
          Rolling 5-game win rate across all 30 NBA teams
        </p>
      </div>

      {isLoading ? (
        <div className="text-muted text-center py-10">Loading streaks…</div>
      ) : (
        <>
          {/* On Fire / Hot */}
          <section>
            <h2 className="font-display font-bold mb-4" style={{ fontSize: '22px', color: '#ef4444' }}>
              On Fire
            </h2>
            {hotTeams.length === 0 ? (
              <p className="text-muted">No teams currently on a hot streak.</p>
            ) : (
              <div className="flex gap-4 overflow-x-auto pb-2">
                {hotTeams.map((t) => (
                  <StreakCard key={t.team_abbr} {...t} />
                ))}
              </div>
            )}
          </section>

          {/* Cold Spell */}
          <section>
            <h2 className="font-display font-bold mb-4" style={{ fontSize: '22px', color: '#60a5fa' }}>
              Cold Spell
            </h2>
            {coldTeams.length === 0 ? (
              <p className="text-muted">No teams currently in a cold streak.</p>
            ) : (
              <div className="flex gap-4 overflow-x-auto pb-2">
                {coldTeams.map((t) => (
                  <StreakCard key={t.team_abbr} {...t} />
                ))}
              </div>
            )}
          </section>

          {/* All Teams Bar Chart */}
          {rows.length > 0 && (
            <div className="card p-6">
              <h2 className="font-display font-bold text-white mb-4" style={{ fontSize: '20px' }}>
                All Teams — 5-Game Win Rate
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={rows}
                  margin={{ top: 0, right: 10, left: -20, bottom: 0 }}
                >
                  <XAxis
                    dataKey="team_abbr"
                    tick={{ fill: '#8b9ab5', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    interval={0}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tick={{ fill: '#8b9ab5', fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
                  />
                  <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                  <Bar dataKey="rolling_5game_win_rate" radius={[4, 4, 0, 0]}>
                    {rows.map((row, i) => (
                      <Cell key={i} fill={barColor(row.rolling_5game_win_rate)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  )
}
