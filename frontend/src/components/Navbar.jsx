// frontend/src/components/Navbar.jsx
import React from 'react'
import { NavLink } from 'react-router-dom'

/**
 * CourtPulse top navigation bar.
 * - Fixed glass-morphism background
 * - Left: 🏀 CourtPulse logo
 * - Right: Overview | Players | Streaks | Live (pulsing dot)
 */
export default function Navbar() {
  const linkClass = ({ isActive }) =>
    [
      'relative px-3 py-1.5 text-sm font-medium transition-colors duration-200',
      isActive
        ? 'text-electric after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-electric after:rounded-full'
        : 'text-ice/60 hover:text-ice',
    ].join(' ')

  return (
    <nav
      className="fixed top-0 inset-x-0 z-50 h-16 flex items-center px-6 lg:px-10"
      style={{
        background: 'rgba(10,14,26,0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(59,130,246,0.15)',
        boxShadow: '0 2px 24px rgba(0,0,0,0.5)',
      }}
    >
      {/* ── Logo ─────────────────────────────────────────────────────── */}
      <NavLink
        to="/"
        className="flex items-center gap-2 mr-10 select-none"
        style={{ textDecoration: 'none' }}
      >
        <span className="text-2xl" aria-hidden="true">🏀</span>
        <span
          className="text-2xl font-extrabold tracking-wide text-ice"
          style={{ fontFamily: '"Barlow Condensed", sans-serif' }}
        >
          Court<span className="text-electric">Pulse</span>
        </span>
      </NavLink>

      {/* ── Navigation links ──────────────────────────────────────────── */}
      <div className="flex items-center gap-1 ml-auto">
        <NavLink to="/" end className={linkClass} id="nav-overview">
          Overview
        </NavLink>

        <NavLink to="/players" className={linkClass} id="nav-players">
          Players
        </NavLink>

        <NavLink to="/streaks" className={linkClass} id="nav-streaks">
          Streaks
        </NavLink>

        {/* Live — with pulsing red indicator */}
        <NavLink to="/live" className={linkClass} id="nav-live">
          <span className="flex items-center gap-1.5">
            <span className="live-dot" aria-hidden="true" />
            Live
          </span>
        </NavLink>
      </div>
    </nav>
  )
}
