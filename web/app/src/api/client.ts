import axios, { AxiosError } from 'axios'
import { useAuth } from '../store/auth'
import type { TokenPair } from './types'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = useAuth.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string | null> | null = null

async function tryRefresh(): Promise<string | null> {
  const { refreshToken, setSession, logout } = useAuth.getState()
  if (!refreshToken) return null
  try {
    const { data } = await axios.post<TokenPair>('/api/refresh', { refresh_token: refreshToken })
    setSession(data.access_token, data.refresh_token, data.user)
    return data.access_token
  } catch {
    logout()
    return null
  }
}

api.interceptors.response.use(undefined, async (error: AxiosError) => {
  const original = error.config
  if (error.response?.status === 401 && original && !('_retried' in original)) {
    refreshing ??= tryRefresh().finally(() => (refreshing = null))
    const token = await refreshing
    if (token) {
      Object.assign(original, { _retried: true })
      original.headers.Authorization = `Bearer ${token}`
      return api.request(original)
    }
  }
  throw error
})

/** Human-readable message from an API error (422 field errors, HTTPException details). */
export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as
      | { detail?: string | { loc: (string | number)[]; msg: string }[] }
      | undefined
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail))
      return data.detail
        .map((d) => `Required: ${d.loc.slice(1).join('.')} — ${d.msg}`)
        .join('; ')
  }
  return 'Something went wrong'
}
