import type { Card, Draft, User } from './types'

export class ApiRequestError extends Error {
  status: number
  code: string
  fields: string[]

  constructor(status: number, code: string, message: string, fields: string[] = []) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

// 요청이 서버에 닿지 못한 경우(연결 끊김 등)에 쓰는 code.
export const NETWORK_ERROR = 'NETWORK_ERROR'

// 로그인 밖에서 401 UNAUTHENTICATED 를 받으면 부른다. App 이 로그인 화면으로 보낸다.
let onUnauthenticated: (() => void) | null = null

export function setUnauthenticatedHandler(handler: (() => void) | null): void {
  onUnauthenticated = handler
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response
  try {
    // 세션은 HttpOnly 쿠키라 화면 코드가 만지지 않는다.
    res = await fetch(path, { ...init, credentials: 'same-origin' })
  } catch {
    throw new ApiRequestError(0, NETWORK_ERROR, '서버에 연결하지 못했다.')
  }

  if (!res.ok) {
    let body: { error?: { code?: string; message?: string; fields?: string[] } } = {}
    try {
      body = await res.json()
    } catch {
      // 본문이 JSON 이 아니면 code 를 비워 둔다.
    }
    if (res.status === 401 && body.error?.code === 'UNAUTHENTICATED' && !path.startsWith('/api/auth/')) {
      onUnauthenticated?.()
    }
    throw new ApiRequestError(
      res.status,
      body.error?.code ?? 'UNKNOWN',
      body.error?.message ?? res.statusText,
      body.error?.fields ?? [],
    )
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export function listCards(): Promise<{ items: Card[] }> {
  return request('/api/cards')
}

export function createCards(items: Draft[]): Promise<{ items: Card[] }> {
  return request('/api/cards', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  })
}

export type CardPatch = Partial<Pick<Card, 'name' | 'quantity' | 'due_date' | 'storage' | 'is_risky'>>

export function updateCard(id: string, patch: CardPatch): Promise<Card> {
  return request(`/api/cards/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
}

// 정리: 카드를 지우지 않고 상태만 '정리됨'으로 바꾼다. 목록에는 남은 카드만 나온다.
export function archiveCard(id: string): Promise<Card> {
  return request(`/api/cards/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: 'archived' }),
  })
}

export function analyzeReceipt(image: File): Promise<{ items: Draft[] }> {
  const form = new FormData()
  form.append('image', image)
  return request('/api/receipts/analyze', { method: 'POST', body: form })
}

const jsonPost = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export function signup(loginId: string, password: string): Promise<{ user: User }> {
  return request('/api/auth/signup', jsonPost({ login_id: loginId, password }))
}

export function login(loginId: string, password: string): Promise<{ user: User }> {
  return request('/api/auth/login', jsonPost({ login_id: loginId, password }))
}

export function logout(): Promise<void> {
  return request('/api/auth/logout', { method: 'POST' })
}

export function me(): Promise<{ user: User }> {
  return request('/api/auth/me')
}
