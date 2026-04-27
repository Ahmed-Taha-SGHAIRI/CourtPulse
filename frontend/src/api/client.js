import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getStandings = (conference) =>
  api.get('/standings', { params: conference ? { conference } : {} })

export const getPlayers = (params) => api.get('/players', { params })

export const getStreaks = () => api.get('/streaks')

export const getLive = () => api.get('/live')

export const getKpis = () => api.get('/kpis')
