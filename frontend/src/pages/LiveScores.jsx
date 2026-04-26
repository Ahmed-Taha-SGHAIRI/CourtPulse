// frontend/src/pages/LiveScores.jsx
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import axios from 'axios'
import LiveScoreCard from '../components/LiveScoreCard.jsx'

const fetcher = (url) => axios.get(url).then(r => r.data)

export default function LiveScores() {
  const { data: games = [], isLoading, dataUpdatedAt } = useQuery({
    queryKey:       ['live'],
    queryFn:        () => fetcher('/api/live'),
    refetchInterval: 30_000,   // auto-refresh every 30 s
    staleTime:       25_000,
  })

  const lastUpdated = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : '—'

  return (
    <div className="space-y-6">
      {/* Page title + meta bar */}
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold text-ice tracking-wide">
            Live Scores
          </h1>
          <p className="text-sm text-muted mt-1">
            Auto-refreshes every 30 seconds via Kafka stream
          </p>
        </div>

        {/* Active game count + last updated */}
        <div className="flex items-center gap-4">
          {games.length > 0 && (
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold"
              style={{ background: 'rgba(16,185,129,0.15)', color: '#10b981', border: '1px solid rgba(16,185,129,0.3)' }}
            >
              <span className="live-dot" />
              {games.length} game{games.length !== 1 ? 's' : ''} live
            </div>
          )}
          <span className="text-xs text-muted">
            Updated: {lastUpdated}
          </span>
        </div>
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="glass-card h-52 animate-pulse" />
          ))}
        </div>
      )}

      {/* No games state */}
      {!isLoading && games.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 text-center gap-4">
          <span className="text-6xl" aria-hidden="true">🏀</span>
          <h2 className="font-display text-2xl font-bold text-ice">
            No games currently live
          </h2>
          <p className="text-muted text-sm max-w-sm">
            Check back during game time, or make sure the Kafka producer container is running.
          </p>
          <p className="text-xs text-muted/60">Last checked: {lastUpdated}</p>
        </div>
      )}

      {/* Live game cards grid */}
      {!isLoading && games.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {games.map((game, i) => (
            <LiveScoreCard key={game.game_id ?? i} game={game} />
          ))}
        </div>
      )}
    </div>
  )
}
