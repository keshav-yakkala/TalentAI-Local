/**
 * TalentAI — Mock API (Demo Mode)
 *
 * When the backend is unavailable, this provides a fully functional demo
 * experience using localStorage as the data store.
 *
 * Pre-seeded demo accounts (always available):
 *   Recruiter: recruiter@talentai.com / Demo@1234
 *   Candidate: candidate@talentai.com / Demo@1234
 */

import type { TokenResponse, User } from '@/types'

const DEMO_USERS_KEY = 'talentai_demo_users'
const DEMO_TOKEN_PREFIX = 'demo_token_'

// ── Backend availability cache ────────────────────────────────────────────────

let _backendAvailable: boolean | null = null
let _lastCheck = 0
const CACHE_TTL_MS = 30_000

export async function checkBackendAvailable(): Promise<boolean> {
  const now = Date.now()
  if (_backendAvailable !== null && now - _lastCheck < CACHE_TTL_MS) {
    return _backendAvailable
  }
  try {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 2000)
    const res = await fetch('/api/v1/health', { signal: controller.signal })
    clearTimeout(timeout)
    _backendAvailable = res.ok
  } catch {
    _backendAvailable = false
  }
  _lastCheck = Date.now()
  return _backendAvailable
}

export function resetBackendCache() {
  _backendAvailable = null
  _lastCheck = 0
}

export function isBackendDown(err: unknown): boolean {
  if (!err || typeof err !== 'object') return false
  const e = err as Record<string, unknown>
  if (e.code === 'ERR_NETWORK' || e.code === 'ECONNREFUSED' || e.code === 'ENOTFOUND') return true
  const status = (e.response as Record<string, unknown> | undefined)?.status as number | undefined
  if (status === 502 || status === 503 || status === 504) return true
  if (!e.response) return true
  return false
}

// ── Demo user store ───────────────────────────────────────────────────────────

interface StoredUser {
  id: string
  email: string
  password: string
  full_name: string
  role: 'recruiter' | 'candidate' | 'admin'
  is_active: boolean
  created_at: string
}

// Pre-seeded demo users — always available, injected on first load
const SEED_USERS: StoredUser[] = [
  {
    id: 'demo-recruiter-001',
    email: 'recruiter@talentai.com',
    password: 'Demo@1234',
    full_name: 'Demo Recruiter',
    role: 'recruiter',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'demo-candidate-001',
    email: 'candidate@talentai.com',
    password: 'Demo@1234',
    full_name: 'Demo Candidate',
    role: 'candidate',
    is_active: true,
    created_at: '2025-01-01T00:00:00Z',
  },
]

function getUsers(): StoredUser[] {
  try {
    const stored = JSON.parse(localStorage.getItem(DEMO_USERS_KEY) || '[]') as StoredUser[]
    // Ensure seed users are always present
    const ids = stored.map((u) => u.id)
    const missing = SEED_USERS.filter((s) => !ids.includes(s.id))
    if (missing.length > 0) {
      const merged = [...missing, ...stored]
      localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(merged))
      return merged
    }
    return stored
  } catch {
    localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(SEED_USERS))
    return SEED_USERS
  }
}

function saveUsers(users: StoredUser[]) {
  localStorage.setItem(DEMO_USERS_KEY, JSON.stringify(users))
}

function generateId(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

function makeTokens(userId: string): TokenResponse {
  return {
    access_token: `${DEMO_TOKEN_PREFIX}${userId}`,
    refresh_token: `${DEMO_TOKEN_PREFIX}refresh_${userId}`,
    token_type: 'bearer',
    expires_in: 3600,
  }
}

function storedToUser(u: StoredUser): User {
  return {
    id: u.id,
    email: u.email,
    full_name: u.full_name,
    role: u.role,
    is_active: u.is_active,
    created_at: u.created_at,
  }
}

// ── Mock API ──────────────────────────────────────────────────────────────────

export const mockApi = {
  isDemoToken(token: string | null): boolean {
    return !!token?.startsWith(DEMO_TOKEN_PREFIX)
  },

  /** Ensure seed users exist (call on app mount) */
  init() {
    getUsers() // triggers seed injection
  },

  register(data: {
    email: string
    password: string
    full_name: string
    role: 'recruiter' | 'candidate'
  }): { tokens: TokenResponse; user: User } {
    const users = getUsers()
    if (users.find((u) => u.email.toLowerCase() === data.email.toLowerCase())) {
      throw { response: { status: 409, data: { detail: 'An account with this email already exists.' } } }
    }
    const newUser: StoredUser = {
      id: generateId(),
      email: data.email,
      password: data.password,
      full_name: data.full_name,
      role: data.role,
      is_active: true,
      created_at: new Date().toISOString(),
    }
    users.push(newUser)
    saveUsers(users)
    return { tokens: makeTokens(newUser.id), user: storedToUser(newUser) }
  },

  login(email: string, password: string): { tokens: TokenResponse; user: User } {
    const users = getUsers()
    const user = users.find(
      (u) => u.email.toLowerCase() === email.toLowerCase() && u.password === password
    )
    if (!user) {
      throw { response: { status: 401, data: { detail: 'Invalid email or password.' } } }
    }
    return { tokens: makeTokens(user.id), user: storedToUser(user) }
  },

  me(token: string | null): User {
    if (!token?.startsWith(DEMO_TOKEN_PREFIX)) {
      throw { response: { status: 401, data: { detail: 'Not authenticated' } } }
    }
    const userId = token.replace(DEMO_TOKEN_PREFIX, '')
    const user = getUsers().find((u) => u.id === userId)
    if (!user) throw { response: { status: 401, data: { detail: 'Session expired' } } }
    return storedToUser(user)
  },
}
