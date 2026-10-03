import type { Account, Product, ProductDetail } from './types.ts'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function errorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown }
    if (typeof body.detail === 'string' && body.detail) return body.detail
  } catch {
    // The body was not JSON.
  }
  return fallback
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response, `Request failed for ${path}`))
  }
  return response.json() as Promise<T>
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response, 'Request failed.'))
  }
  return response.json() as Promise<T>
}

export function listProducts(): Promise<Product[]> {
  return getJson<Product[]>('/api/products')
}

export function getProduct(productId: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

export type NewAccount = {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

export function loginAccount(email: string, password: string): Promise<Account> {
  return postJson<Account>('/api/auth/login', { email, password })
}

export function registerAccount(account: NewAccount): Promise<Account> {
  return postJson<Account>('/api/auth/register', account)
}

export function logoutAccount(): Promise<void> {
  return postJson<{ ok: boolean }>('/api/auth/logout', {}).then(() => undefined)
}

export async function currentAccount(): Promise<Account | null> {
  const response = await fetch('/api/auth/me', { credentials: 'include' })
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response, 'Could not check the account.'))
  }
  const body = (await response.json()) as { user: Account | null }
  return body.user
}

export function formatPrice(price: number): string {
  return price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}
