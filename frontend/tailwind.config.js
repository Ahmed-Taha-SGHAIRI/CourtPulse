/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        navy:     '#0a0e1a',
        court:    '#1a2035',
        electric: '#3b82f6',
        amber:    '#f59e0b',
        ice:      '#e0f2fe',
        emerald:  '#10b981',
        danger:   '#ef4444',
        surface:  '#111827',
        muted:    '#6b7280',
      },
      fontFamily: {
        display: ['"Barlow Condensed"', 'sans-serif'],
        body:    ['"Inter"', 'sans-serif'],
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':     'fadeIn 0.4s ease-in-out',
        'slide-up':    'slideUp 0.4s ease-out',
        'count-up':    'countUp 0.8s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        glass:  '0 4px 32px rgba(0,0,0,0.4)',
        glow:   '0 0 20px rgba(59,130,246,0.35)',
        amber:  '0 0 20px rgba(245,158,11,0.35)',
        green:  '0 0 20px rgba(16,185,129,0.35)',
      },
    },
  },
  plugins: [],
}
