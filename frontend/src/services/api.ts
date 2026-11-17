import type { Run, Settings, Stats } from '../types'

const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const TOKEN_KEY = 'pipeline-doctor-token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  })

  if (response.status === 401) {
    throw new Error('That API token was rejected. Check it in Settings.')
  }
  if (!response.ok) {
    throw new Error(`The API returned an error (${response.status}). Try again shortly.`)
  }

  return response.json() as Promise<T>
}

export async function getDashboard() {
  const [runs, stats] = await Promise.all([
    request<Run[]>('/api/v1/runs?limit=100'),
    request<Stats>('/api/v1/stats'),
  ])
  return { runs, stats }
}

export function getRun(id: number) {
  return request<Run>(`/api/v1/runs/${id}`)
}

export function getSettings() {
  return request<Settings>('/api/v1/settings')
}

export function healthUrl() {
  return `${API_URL}/health`
}
