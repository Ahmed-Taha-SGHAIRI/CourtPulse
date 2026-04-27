import React from 'react'
import { NavLink } from 'react-router-dom'

const links = [
  { to: '/', label: 'Overview' },
  { to: '/players', label: 'Players' },
  { to: '/streaks', label: 'Streaks' },
  { to: '/live', label: 'Live', live: true },
]

export default function Navbar() {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6"
      style={{
        height: '56px',
        background: '#080d1a',
        borderBottom: '1px solid rgba(79,142,247,0.2)',
      }}
    >
      {/* Brand */}
      <span
        className="font-display font-bold select-none"
        style={{ fontSize: '22px', color: '#4f8ef7', letterSpacing: '0.02em' }}
      >
        CourtPulse
      </span>

      {/* Nav links */}
      <div className="flex items-center gap-6">
        {links.map(({ to, label, live }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              [
                'flex items-center gap-1.5 text-sm font-medium pb-0.5 transition-colors',
                isActive
                  ? 'text-electric border-b border-electric'
                  : 'text-muted hover:text-white',
              ].join(' ')
            }
          >
            {live && (
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse inline-block" />
            )}
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
