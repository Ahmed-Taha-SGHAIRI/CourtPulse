import React from 'react'

const statusColor = {
  Playoff: '#22c55e',
  'Play-In': '#f0b429',
  Eliminated: '#374151',
}

const statusBg = {
  Playoff: 'rgba(34,197,94,0.12)',
  'Play-In': 'rgba(240,180,41,0.12)',
  Eliminated: 'rgba(55,65,81,0.3)',
}

function StatusBadge({ status }) {
  const color = statusColor[status] || '#8b9ab5'
  const bg = statusBg[status] || 'rgba(139,154,181,0.1)'
  return (
    <span
      className="badge"
      style={{ color, background: bg, border: `1px solid ${color}40` }}
    >
      {status}
    </span>
  )
}

export default function StandingsTable({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="text-muted text-center py-10">No standings data available.</div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl" style={{ border: '1px solid rgba(79,142,247,0.12)' }}>
      <table className="cp-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Team</th>
            <th>W</th>
            <th>L</th>
            <th>Win%</th>
            <th>Home</th>
            <th>Away</th>
            <th>PPG</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => {
            const borderColor = statusColor[row.playoff_status] || '#374151'
            return (
              <tr
                key={row.team_id ?? i}
                style={{ borderLeft: `3px solid ${borderColor}` }}
              >
                <td className="text-muted stat-number" style={{ fontSize: '16px' }}>
                  {row.conference_rank}
                </td>
                <td>
                  <span className="font-semibold text-white">{row.team_abbreviation}</span>
                  <span className="text-muted ml-2" style={{ fontSize: '13px' }}>
                    {row.team_name}
                  </span>
                </td>
                <td className="text-win font-bold">{row.wins}</td>
                <td className="text-loss font-bold">{row.losses}</td>
                <td className="stat-number" style={{ color: '#4f8ef7', fontSize: '16px' }}>
                  {row.win_pct != null ? (row.win_pct * 100).toFixed(1) + '%' : '—'}
                </td>
                <td className="text-muted">{row.home_record || '—'}</td>
                <td className="text-muted">{row.road_record || '—'}</td>
                <td className="stat-number" style={{ fontSize: '15px' }}>
                  {row.avg_pts_scored ?? '—'}
                </td>
                <td>
                  <StatusBadge status={row.playoff_status} />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
