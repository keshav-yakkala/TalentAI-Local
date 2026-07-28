/**
 * Auth store — Zustand
 * Manages JWT tokens and user session.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, TokenResponse } from '@/types'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setAuth: (user: User, tokens: TokenResponse) => void
  clearAuth: () => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setAuth: (user, tokens) => {
        localStorage.setItem('talentai_access_token', tokens.access_token)
        localStorage.setItem('talentai_refresh_token', tokens.refresh_token)
        set({
          user,
          accessToken: tokens.access_token,
          refreshToken: tokens.refresh_token,
          isAuthenticated: true,
        })
      },

      clearAuth: () => {
        localStorage.removeItem('talentai_access_token')
        localStorage.removeItem('talentai_refresh_token')
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
      },

      logout: () => {
        localStorage.removeItem('talentai_access_token')
        localStorage.removeItem('talentai_refresh_token')
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false })
        window.location.href = '/login'
      },
    }),
    {
      name: 'talentai-auth',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
