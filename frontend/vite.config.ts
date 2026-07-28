import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  const grokApiKey = env.GROK_API_KEY || ''

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
        },
        '/grok-api': {
          target: 'https://api.x.ai',
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/grok-api/, ''),
          headers: {
            Authorization: `Bearer ${grokApiKey}`,
          },
        },
        '/ollama': {
          target: 'http://localhost:11434',
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/ollama/, ''),
        },
      },
    },
  }
})
