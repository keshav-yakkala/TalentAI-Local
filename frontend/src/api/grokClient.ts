/**
 * Grok (xAI) LLM API Client for React Frontend.
 * High-performance Cloud AI inference using xAI's Grok API.
 */

export interface GrokMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export const GROK_MODEL = 'grok-2-latest'

export async function grokChat(
  messages: GrokMessage[],
  opts: { json?: boolean; timeout?: number; model?: string; temperature?: number } = {}
): Promise<string> {
  const model = opts.model || GROK_MODEL
  const apiKey = (import.meta.env.VITE_GROK_API_KEY || '').trim()

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  let url = 'https://api.x.ai/v1/chat/completions'
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`
  } else {
    url = '/grok-api/v1/chat/completions'
  }

  const controller = new AbortController()
  const timeoutMs = opts.timeout ?? 60_000
  const t = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const res = await fetch(url, {
      method: 'POST',
      headers,
      signal: controller.signal,
      body: JSON.stringify({
        model,
        messages,
        temperature: opts.temperature ?? 0.2,
        stream: false,
      }),
    })
    clearTimeout(t)

    if (!res.ok) {
      const errText = await res.text().catch(() => '')
      throw new Error(`Grok API ${res.status}: ${errText.slice(0, 200)}`)
    }

    const data = (await res.json()) as {
      choices?: Array<{ message?: { content: string } }>
    }

    return data.choices?.[0]?.message?.content?.trim() ?? ''
  } catch (err) {
    clearTimeout(t)
    throw err
  }
}
