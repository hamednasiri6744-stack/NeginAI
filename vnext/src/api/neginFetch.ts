export class NeginGeneratedApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'NeginGeneratedApiError'
  }
}

export async function neginFetch<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: 'include',
    cache: 'no-store',
  })
  if (!response.ok) throw new NeginGeneratedApiError(response.status, await response.text())
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
