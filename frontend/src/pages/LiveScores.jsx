import React, { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLive } from '../api/client'
import LiveScoreCard from '../components/LiveScoreCard'

export default function LiveScores() {
  const [lastUpdated, setLastUpdated] = useState(null)

  const { data: games, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['live'],
    queryFn: () => getLive().then((r) => r.data),
    refetchInterval: 30000,
  })

  useEffect(() => {
    if (dataUpdatedAt) {
      setLastUpdated(new Date(dataUpdatedAt))
    }
  }, [dataUpdatedAt])

  const rows = games || []
  const activeCount = rows.filter(
    (g) => g.status && !g.status.toLowerCase().includes('final')
  ).length

  return (
    <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col gap-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="font-display font-bold text-white" style={{ fontSize: '32px' }}>
            Live Games
          </h1>
          <p className="text-muted mt-1" style={{ fontSize: '14px' }}>
            Auto-refreshes every 30 seconds via Kafka streaming
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {activeCount > 0 && (
            <div
              className="flex items-center gap-2 px-3 py-1 rounded-full"
              style={{ background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.3)' }}
            >
              <span className="w-2 h-2 rounded-full bg-win animate-pulse" />
              <span className="text-win text-sm font-semibold">{activeCount} Live</span>
            </div>
          )}
          {lastUpdated && (
            <span className="text-muted" style={{ fontSize: '12px' }}>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="text-muted text-center py-16">Loading live scores…</div>
      ) : rows.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-24 gap-4"
          style={{ color: '#8b9ab5' }}
        >
          <span style={{ fontSize: '56px' }}></span>
          <p className="font-semibold text-white" style={{ fontSize: '18px' }}>
            No live games right now
          </p>
          <p style={{ fontSize: '14px' }}>Check back during game time</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {rows.map((game, i) => (
              <LiveScoreCard key={game.game_key ?? i} game={game} />
            ))}
          </div>
          {lastUpdated && (
            <p className="text-muted text-center" style={{ fontSize: '12px' }}>
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </>
      )}
    </div>
  )
}
