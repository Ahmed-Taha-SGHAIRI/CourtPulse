// frontend/src/components/KpiCard.jsx
import React, { useEffect, useRef, useState } from 'react'

/**
 * KpiCard — animated metric card with count-up effect.
 *
 * Props:
 *   title    {string}  — card label
 *   value    {string|number} — main display value
 *   subtitle {string}  — secondary line
 *   icon     {string}  — emoji icon
 *   trend    {'up'|'down'|null}
 */
export default function KpiCard({ title, value, subtitle, icon, trend }) {
  const isNumeric = typeof value === 'number' || !isNaN(Number(value))
  const targetNum = isNumeric ? Number(value) : null

  const [displayed, setDisplayed] = useState(0)
  const animRef = useRef(null)

  /* Count-up animation on mount */
  useEffect(() => {
    if (targetNum === null) return
    const start = 0
    const end = targetNum
    const duration = 900
    const startTime = performance.now()

    const step = (now) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayed(Math.round(start + eased * (end - start)))
      if (progress < 1) {
        animRef.current = requestAnimationFrame(step)
      }
    }
    animRef.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(animRef.current)
  }, [targetNum])

  const displayValue = targetNum !== null ? displayed : value

  return (
    <div
      className="glass-card border-top-electric p-5 flex flex-col gap-2 animate-slide-up"
      style={{ minWidth: 0 }}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-muted uppercase tracking-widest">
          {title}
        </span>
        <span className="text-2xl" aria-hidden="true">{icon}</span>
      </div>

      {/* Main value */}
      <div className="flex items-end gap-2">
        <span
          className="text-3xl font-extrabold text-ice leading-none"
          style={{ fontFamily: '"Barlow Condensed", sans-serif' }}
        >
          {displayValue}
        </span>

        {/* Trend arrow */}
        {trend === 'up' && (
          <span className="text-emerald text-lg font-bold mb-0.5">↑</span>
        )}
        {trend === 'down' && (
          <span className="text-danger text-lg font-bold mb-0.5">↓</span>
        )}
      </div>

      {/* Subtitle */}
      {subtitle && (
        <p className="text-xs text-muted truncate">{subtitle}</p>
      )}
    </div>
  )
}
