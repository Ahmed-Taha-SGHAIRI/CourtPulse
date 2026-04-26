// frontend/src/App.jsx
import React from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import Overview from './pages/Overview.jsx'
import Players from './pages/Players.jsx'
import Streaks from './pages/Streaks.jsx'
import LiveScores from './pages/LiveScores.jsx'

/**
 * PageWrapper — adds per-page fade-in animation via CSS class.
 */
function PageWrapper({ children }) {
  const { pathname } = useLocation()
  return (
    <div key={pathname} className="animate-fade-in">
      {children}
    </div>
  )
}

/**
 * AppRoutes — defines all page routes.
 */
function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<PageWrapper><Overview /></PageWrapper>} />
      <Route path="/players" element={<PageWrapper><Players /></PageWrapper>} />
      <Route path="/streaks" element={<PageWrapper><Streaks /></PageWrapper>} />
      <Route path="/live" element={<PageWrapper><LiveScores /></PageWrapper>} />
      {/* Catch-all → Overview */}
      <Route path="*" element={<PageWrapper><Overview /></PageWrapper>} />
    </Routes>
  )
}

/**
 * App root — router + navbar + page content.
 */
export default function App() {
  return (
    <BrowserRouter>
      {/* Fixed top navigation */}
      <Navbar />

      {/* Main content area — padded below navbar */}
      <main className="pt-16 min-h-screen bg-navy">
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <AppRoutes />
        </div>
      </main>
    </BrowserRouter>
  )
}
