/// <reference types="vite/client" />
/**
 * TalentAI — Typed API client
 * All API calls go through this module.
 * Base URL configurable via VITE_API_BASE_URL.
 */
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ── Request interceptor: attach JWT ──────────────────────────────────────────

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('talentai_access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: handle 401 globally ─────────────────────────────────

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Attempt token refresh
      const refreshToken = localStorage.getItem('talentai_refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken,
          })
          localStorage.setItem('talentai_access_token', data.access_token)
          localStorage.setItem('talentai_refresh_token', data.refresh_token)
          // Retry original request
          if (error.config) {
            error.config.headers.Authorization = `Bearer ${data.access_token}`
            return apiClient.request(error.config)
          }
        } catch {
          // Refresh failed — clear auth and redirect to login
          localStorage.removeItem('talentai_access_token')
          localStorage.removeItem('talentai_refresh_token')
          window.location.href = '/login'
        }
      } else {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
