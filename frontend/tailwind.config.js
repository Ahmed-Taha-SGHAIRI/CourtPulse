/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        navy: '#080d1a',
        court: '#0f1729',
        card: '#141e33',
        electric: '#4f8ef7',
        gold: '#f0b429',
        win: '#22c55e',
        loss: '#ef4444',
        muted: '#8b9ab5',
      },
      fontFamily: {
        display: ['Barlow Condensed', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
