import React from 'react'

export default function KpiCard({ title, value, subtitle, icon }) {
  return (
    <div className="card p-6 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span style={{ fontSize: '24px' }}>{icon}</span>
        <span
          className="text-muted font-medium tracking-widest"
          style={{ fontSize: '12px', textTransform: 'uppercase' }}
        >
          {title}
        </span>
      </div>
      <div
        className="stat-number text-white"
        style={{ fontSize: '36px', lineHeight: 1 }}
      >
        {value ?? '—'}
      </div>
      {subtitle && (
        <div className="text-muted" style={{ fontSize: '13px' }}>
          {subtitle}
        </div>
      )}
    </div>
  )
}
