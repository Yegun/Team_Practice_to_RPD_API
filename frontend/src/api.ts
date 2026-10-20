import { getOwnerId } from './ownerId'
import type { Card, Draft } from './types'

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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('X-Owner-Id', getOwnerId())

  let res: Response
  try {
    res = await fetch(path, { ...init, headers })
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
    throw new ApiRequestError(
      res.status,
      body.error?.code ?? 'UNKNOWN',
      body.error?.message ?? res.statusText,
      body.error?.fields ?? [],
    )
  }
  return (await res.json()) as T
}

export function listCards(): Promise<{ items: Card[] }> {
  return request('/api/cards')
}

export function analyzeReceipt(image: File): Promise<{ items: Draft[] }> {
  const form = new FormData()
  form.append('image', image)
  return request('/api/receipts/analyze', { method: 'POST', body: form })
}
