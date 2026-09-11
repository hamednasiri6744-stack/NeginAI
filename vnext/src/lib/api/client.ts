const configuredBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '')
const configuredTimeout = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 15000)

export const apiConfig = {
  baseUrl: configuredBaseUrl,
  timeoutMs: Number.isFinite(configuredTimeout) && configuredTimeout > 0 ? configuredTimeout : 15000,
} as const

export class ApiError extends Error {
  readonly status: number
  readonly payload: unknown
  readonly requestId: string | null
  readonly kind: 'http' | 'network' | 'timeout' | 'aborted'

  constructor(
    status: number,
    payload: unknown,
    requestId: string | null,
    message: string,
    kind: 'http' | 'network' | 'timeout' | 'aborted' = 'http',
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
    this.requestId = requestId
    this.kind = kind
  }
}

function errorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === 'object') {
    const value = payload as Record<string, unknown>
    for (const key of ['detail', 'error', 'message']) {
      if (typeof value[key] === 'string' && value[key]) return value[key] as string
    }
  }
  return fallback
}

function requestUrl(path: string) {
  if (/^https?:\/\//i.test(path)) return path
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${apiConfig.baseUrl}${normalizedPath}`
}

function mergeSignals(external: AbortSignal | null | undefined, timeoutMs: number) {
  const controller = new AbortController()
  let timedOut = false
  const onAbort = () => controller.abort(external?.reason)

  if (external?.aborted) controller.abort(external.reason)
  else external?.addEventListener('abort', onAbort, { once: true })

  const timer = window.setTimeout(() => {
    timedOut = true
    controller.abort(new DOMException('Request timeout', 'TimeoutError'))
  }, timeoutMs)

  return {
    signal: controller.signal,
    didTimeout: () => timedOut,
    cleanup: () => {
      window.clearTimeout(timer)
      external?.removeEventListener('abort', onAbort)
    },
  }
}

export async function apiRequest<T>(
  path: string,
  init: Omit<RequestInit, 'body'> & { body?: unknown; timeoutMs?: number } = {},
): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  let body: BodyInit | undefined

  if (init.body !== undefined) {
    if (init.body instanceof FormData || init.body instanceof Blob || typeof init.body === 'string') {
      body = init.body as BodyInit
    } else {
      headers.set('Content-Type', 'application/json')
      body = JSON.stringify(init.body)
    }
  }

  const timeoutMs = init.timeoutMs ?? apiConfig.timeoutMs
  const { signal, didTimeout, cleanup } = mergeSignals(init.signal, timeoutMs)

  try {
    const response = await fetch(requestUrl(path), {
      ...init,
      headers,
      body,
      signal,
      credentials: 'include',
    })

    const contentType = response.headers.get('content-type') ?? ''
    const payload =
      response.status === 204
        ? null
        : contentType.includes('application/json')
          ? await response.json().catch(() => null)
          : await response.text().catch(() => '')

    if (!response.ok) {
      throw new ApiError(
        response.status,
        payload,
        response.headers.get('x-request-id'),
        errorMessage(payload, `Request failed with status ${response.status}`),
      )
    }

    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (signal.aborted) {
      if (didTimeout()) throw new ApiError(0, null, null, 'Request timed out', 'timeout')
      throw new ApiError(0, null, null, 'Request aborted', 'aborted')
    }
    throw new ApiError(0, null, null, error instanceof Error ? error.message : 'Network request failed', 'network')
  } finally {
    cleanup()
  }
}
