export type AuthProfile = {
  authenticated?: boolean
  username: string
  personnel_id: number | null
  full_name: string
  role: string
  branch: string
  sales_line: string
  phone: string
  phone_status: string
  supervisor_personnel_id: number | null
  must_change_password: boolean
  active: boolean
  permissions: string[]
  position?: unknown
}

export type SellerRoute = {
  id: string
  title: string
  row_index?: number | null
  updated_at?: string
  customer_count?: number
  source?: string
  is_day_route?: boolean
  can_start_day_route?: boolean
  can_start_visit?: boolean
}

export type SellerRoutesResponse = {
  seller: { personnel_id: number; full_name: string }
  visit_template: string
  routes: SellerRoute[]
  day_route: { id: string; title: string; date?: string; source?: string } | null
  day_route_status: string
  test_all_routes_override?: boolean
  visit_location_policy?: Record<string, unknown>
  source?: string
  live_assignment?: boolean
}

export type VisitResolution = {
  status: string
  outcome: string
  outcome_reason: string
  saved_request_count: number
  ended_at: string
}

export type SellerCustomer = {
  id: string | number
  code: string
  name: string
  store_name: string
  address: string
  latitude: number | null
  longitude: number | null
  location_source?: string
  location_check_exempt?: boolean
  phone: string
  mobile: string
  visit_resolution?: VisitResolution | null
  cardex_balance: number
  open_invoice_remaining: number
  open_invoice_count: number
  financial_snapshot?: {
    bed_credit?: number
    remaining_bed_credit?: number
    asn_credit?: number
    remaining_asn_credit?: number
    has_bed_credit?: boolean
    has_asn_credit?: boolean
    combined_remaining?: number
    customer_remaining?: number
    open_cheque_count?: number
    open_cheque_amount?: number
    returned_cheque_count?: number
    returned_cheque_amount?: number
    dc_ref?: number | null
    updated_at?: string
    source?: string
  }
}

export type RouteCustomersResponse = {
  route: { id: string; title: string }
  customer_count: number
  customers: SellerCustomer[]
  visit_location_policy?: Record<string, unknown>
  source?: string
  live_assignment?: boolean
}

export type CustomerProfileResponse = {
  route: { id: string; title: string }
  customer: SellerCustomer & {
    unique_id?: string
    alarm?: string
    activity_name?: string
    category_name?: string
    level_name?: string
    owner_type_name?: string
    state_name?: string
    city_name?: string
    county_name?: string
    visit_count?: number
    order_count?: number
    order_line_count?: number
    sum_order_amount?: number
    avg_successful_visit?: number
    ngt_updated_at?: string
    editable?: Record<string, unknown>
  }
  lookups?: Record<string, unknown>
  draft?: Record<string, unknown> | null
  draft_updated_at?: string | null
  visit_controls?: Record<string, unknown>
  editable_contract?: {
    fields?: string[]
    active_fields?: string[]
    source?: string
    write_mode?: string
  }
}

export type ChatResponse = {
  conversation_id: string
  answer: string
  columns?: string[]
  rows?: unknown[][]
  row_count?: number
  execution_time?: number | null
  truncated?: boolean
  sources?: string[]
  sql?: string | null
  clarification_required?: boolean
  report_context?: Record<string, unknown> | null
  presentation?: Record<string, unknown> | null
  total_available_rows?: number | null
}

export class NeginApiError extends Error {
  readonly status: number
  readonly detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'NeginApiError'
    this.status = status
    this.detail = detail
  }
}

function apiBase() {
  return String(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')
}

function apiUrl(path: string) {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${apiBase()}${normalized}`
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body !== undefined && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')

  let response: Response
  try {
    response = await fetch(apiUrl(path), {
      ...init,
      headers,
      credentials: 'include',
      cache: 'no-store',
    })
  } catch {
    throw new NeginApiError(0, 'ارتباط با سرور NeginAI برقرار نشد.')
  }

  const raw = await response.text()
  let payload: unknown = {}
  if (raw) {
    try {
      payload = JSON.parse(raw) as unknown
    } catch {
      payload = raw
    }
  }

  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String((payload as { detail?: unknown }).detail ?? '')
      : typeof payload === 'string'
        ? payload
        : ''
    throw new NeginApiError(response.status, detail || `خطای سرور (${response.status})`)
  }

  return payload as T
}

export const neginApi = {
  async login(username: string, password: string) {
    return request<AuthProfile>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  },

  async me() {
    return request<AuthProfile>('/auth/me')
  },

  async logout() {
    return request<{ authenticated: false }>('/auth/logout', { method: 'POST' })
  },

  async changePassword(currentPassword: string, newPassword: string) {
    return request<AuthProfile>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    })
  },

  async routes() {
    return request<SellerRoutesResponse>('/seller-workspace/routes')
  },

  async routeCustomers(routeId: string) {
    return request<RouteCustomersResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers`)
  },

  async customerProfile(routeId: string, customerId: string) {
    return request<CustomerProfileResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/profile`)
  },

  async chat(
    message: string,
    conversationId?: string,
    options?: { dayRouteId?: string; attachmentContext?: string; attachmentName?: string },
  ) {
    const payload: Record<string, unknown> = { message }
    if (conversationId) payload.conversation_id = conversationId
    if (options?.dayRouteId) {
      payload.day_route_mode = true
      payload.day_route_id = options.dayRouteId
    }
    if (options?.attachmentContext) payload.attachment_context = options.attachmentContext
    if (options?.attachmentName) payload.attachment_name = options.attachmentName
    return request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
}
