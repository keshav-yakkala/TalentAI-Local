/**
 * TalentAI — Ollama API Client
 * Calls Llama 3.2 3B via local Ollama instance (proxied through Vite).
 * Proxy: /ollama/* → http://localhost:11434/*
 */

export const OLLAMA_MODEL = 'llama3.2:3b'
const OLLAMA_FALLBACK_MODELS = ['llama3.2:latest', 'llama3.2', 'llama3:8b', 'llama3:latest']

export interface OllamaMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface OllamaStatus {
  running: boolean
  modelFound: boolean
  activeModel: string | null
  availableModels: string[]
  error?: string
}

// ── Global cached active model ────────────────────────────────────────────────
let cachedActiveModel: string | null = null

export async function checkOllamaStatus(): Promise<OllamaStatus> {
  try {
    const controller = new AbortController()
    const t = setTimeout(() => controller.abort(), 4000)
    const res = await fetch('/ollama/api/tags', { signal: controller.signal })
    clearTimeout(t)

    if (!res.ok) {
      return { running: false, modelFound: false, activeModel: null, availableModels: [], error: `HTTP ${res.status}` }
    }

    const data = await res.json() as { models?: { name: string }[] }
    const models = (data.models || []).map((m) => m.name)

    // Find preferred model or fallback to any installed model
    const preferred = [OLLAMA_MODEL, ...OLLAMA_FALLBACK_MODELS]
    const found = preferred.find((m) => models.some((a) => a === m || a.startsWith(m.split(':')[0])))
    
    // If exact preferred match not found, match by prefix or pick first available model
    let activeModel = found || null
    if (!activeModel && models.length > 0) {
      activeModel = models.find(m => m.includes('llama')) || models[0]
    }

    cachedActiveModel = activeModel

    return {
      running: true,
      modelFound: models.length > 0,
      activeModel: activeModel || OLLAMA_MODEL,
      availableModels: models,
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    return {
      running: false,
      modelFound: false,
      activeModel: null,
      availableModels: [],
      error: msg.includes('abort') ? 'Ollama not responding (timeout)' : 'Cannot connect to Ollama',
    }
  }
}

// ── Core chat call ────────────────────────────────────────────────────────────

export async function ollamaChat(
  messages: OllamaMessage[],
  opts: { json?: boolean; timeout?: number; model?: string; temperature?: number } = {}
): Promise<string> {
  if (!cachedActiveModel) {
    try {
      await checkOllamaStatus()
    } catch {
      /* ignore */
    }
  }

  const model = opts.model || cachedActiveModel || OLLAMA_MODEL
  const controller = new AbortController()
  const timeoutMs = opts.timeout ?? 180_000
  const t = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch('/ollama/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        model,
        messages,
        stream: false,
        ...(opts.json ? { format: 'json' } : {}),
        options: {
          temperature: opts.temperature ?? 0.2,
          top_p: 0.85,
          num_predict: 1024,
        },
      }),
    })
    clearTimeout(t)

    if (!res.ok) {
      const txt = await res.text().catch(() => '')
      throw new Error(`Ollama ${res.status}: ${txt.slice(0, 200)}`)
    }

    const data = await res.json() as { message?: { content: string } }
    return data.message?.content?.trim() ?? ''
  } catch (err) {
    clearTimeout(t)
    if (err instanceof Error && (err.name === 'AbortError' || err.message.includes('aborted'))) {
      throw new Error(`Ollama request timed out after ${Math.round(timeoutMs / 1000)} seconds. Ensure Ollama is running cleanly with model ${model}.`)
    }
    throw err
  }
}

// ── JSON extraction helper ────────────────────────────────────────────────────

export function extractJSON<T = unknown>(raw: string): T | null {
  // 1. Try direct parse
  try { return JSON.parse(raw) as T } catch { /* continue */ }
  // 2. Extract first JSON object
  const objMatch = raw.match(/\{[\s\S]*\}/)
  if (objMatch) { try { return JSON.parse(objMatch[0]) as T } catch { /* continue */ } }
  // 3. Extract first JSON array
  const arrMatch = raw.match(/\[[\s\S]*\]/)
  if (arrMatch) { try { return JSON.parse(arrMatch[0]) as T } catch { /* continue */ } }
  return null
}
