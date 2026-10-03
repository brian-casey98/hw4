export type ChatProduct = {
  product_id: string
  name: string
  garment_type: string
  description: string
  price: number
  image_url: string
  colors?: string[]
}

export type ChatResult = {
  message: string
  products: ChatProduct[]
}

export type PageHint = {
  path: string
  product_id?: string
}

export type SavedChatLine = {
  id: number
  role: 'user' | 'assistant'
  content: string
  products: ChatProduct[]
}

export function pageHint(pathname: string): PageHint {
  const match = /^\/products\/([^/]+)$/.exec(pathname)
  return {
    path: pathname,
    product_id: match ? decodeURIComponent(match[1]) : undefined,
  }
}

export async function loadChatHistory(): Promise<SavedChatLine[]> {
  const response = await fetch('/api/chat/history', { credentials: 'include' })
  if (!response.ok) return []
  const body = (await response.json()) as { messages?: SavedChatLine[] }
  return Array.isArray(body.messages) ? body.messages : []
}

export async function requestAssistantReply(message: string, page: PageHint): Promise<ChatResult> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, page }),
  })
  if (!response.ok) {
    let detail = 'The shop assistant could not answer just now.'
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string' && body.detail) detail = body.detail
    } catch {
      // The error body was not JSON.
    }
    throw new Error(detail)
  }
  return response.json() as Promise<ChatResult>
}
