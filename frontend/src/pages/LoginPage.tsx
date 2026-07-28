import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion } from 'framer-motion'
import { Cpu, Eye, EyeOff, Loader2, AlertCircle, WifiOff } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import apiClient from '@/api/client'
import { mockApi, checkBackendAvailable, isBackendDown } from '@/api/mockApi'
import { useAuthStore } from '@/store/auth'
import type { TokenResponse, User } from '@/types'

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})

type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [isDemoMode, setIsDemoMode] = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const { mutate, isPending, error } = useMutation({
    mutationFn: async (data: FormData): Promise<{ tokens: TokenResponse; user: User }> => {
      const backendUp = await checkBackendAvailable()
      if (!backendUp) {
        setIsDemoMode(true)
        return mockApi.login(data.email, data.password)
      }
      try {
        const { data: tokens } = await apiClient.post<TokenResponse>('/auth/login', data)
        const { data: user } = await apiClient.get<User>('/auth/me', {
          headers: { Authorization: `Bearer ${tokens.access_token}` },
        })
        setIsDemoMode(false)
        return { tokens, user }
      } catch (err: unknown) {
        if (isBackendDown(err)) {
          setIsDemoMode(true)
          return mockApi.login(data.email, data.password)
        }
        throw err
      }
    },
    onSuccess: ({ tokens, user }) => {
      setAuth(user, tokens)
      if (user.role === 'recruiter') navigate('/recruiter/dashboard')
      else if (user.role === 'candidate') navigate('/candidate')
      else navigate('/')
    },
  })

  const errorMessage = error
    ? ((error as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Login failed. Check your credentials.')
    : null

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 right-1/4 w-96 h-96 rounded-full opacity-15 blur-3xl"
          style={{ background: 'radial-gradient(circle, rgba(124,58,237,0.5) 0%, transparent 70%)' }} />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative w-full max-w-md"
      >
        {/* Demo mode banner */}
        {isDemoMode && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3"
          >
            <WifiOff className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-300">Demo Mode Active</p>
              <p className="text-xs text-amber-400/80 mt-0.5">
                Backend offline — using your locally registered account.
              </p>
            </div>
          </motion.div>
        )}

        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <span className="font-outfit font-bold text-xl text-white">TalentAI</span>
          </Link>
          <h1 className="font-outfit text-2xl font-bold text-white mb-1">Welcome back</h1>
          <p className="text-slate-400 text-sm">Sign in to your TalentAI account</p>
        </div>

        <div className="glass-card p-8">
          <form onSubmit={handleSubmit((data) => mutate(data))} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">Email address</label>
              <input
                {...register('email')}
                type="email"
                className="input-field"
                placeholder="alex@company.com"
                id="login-email"
              />
              {errors.email && (
                <p className="text-xs text-red-400 mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-sm font-medium text-slate-300">Password</label>
                <button type="button" className="text-xs text-violet-400 hover:text-violet-300">
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  className="input-field pr-12"
                  placeholder="Your password"
                  id="login-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {errorMessage && (
              <div className="flex items-start gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <p className="text-sm text-red-400">{errorMessage}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={isPending}
              id="login-submit"
              className="btn-primary w-full py-3.5 text-base"
            >
              {isPending ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Signing in...</>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          <p className="text-center text-sm text-slate-400 mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-violet-400 hover:text-violet-300 font-medium">
              Create account
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
