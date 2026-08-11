import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserOut } from '../api/types'
import { queryClient } from '../api/queryClient'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserOut | null
  setSession: (access: string, refresh: string, user: UserOut) => void
  setAccessToken: (access: string) => void
  logout: () => void
}

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setSession: (accessToken, refreshToken, user) => set({ accessToken, refreshToken, user }),
      setAccessToken: (accessToken) => set({ accessToken }),
      logout: () => {
        // Drop cached data so the previous org's data can't show in the next session.
        queryClient.clear()
        set({ accessToken: null, refreshToken: null, user: null })
      },
    }),
    { name: 'coachlink-auth' },
  ),
)
