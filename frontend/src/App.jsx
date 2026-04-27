import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Overview from './pages/Overview'
import Players from './pages/Players'
import Streaks from './pages/Streaks'
import LiveScores from './pages/LiveScores'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <div className="pt-14">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/players" element={<Players />} />
          <Route path="/streaks" element={<Streaks />} />
          <Route path="/live" element={<LiveScores />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
