import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import './index.css'
import { mockApi } from '@/api/mockApi'

// Seed demo users so login always works without backend
mockApi.init()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,   // 5 minutes
      retry: (failureCount, error: unknown) => {
        // Don't retry on 401/403/404
        const status = (error as { response?: { status: number } })?.response?.status
        if (status && [401, 403, 404].includes(status)) return false
        return failureCount < 2
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
