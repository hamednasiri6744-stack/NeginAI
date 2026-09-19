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

export type SellerWorkCalendar = {
  date: string
  month: string
  elapsed_working_days: number
  remaining_working_days: number
  total_working_days: number
  is_working_day: boolean
  source: string
}

export type SellerTargetPulse = {
  configured: boolean
  seller_id: number
  period: string
  actual_sales_rial: number
  actual_invoice_count: number
  target_rial: number | null
  achievement_percent: number | null
  expected_pace_percent: number | null
  pace_gap_percent: number | null
  remaining_target_rial: number | null
  daily_required_rial: number | null
  remaining_working_days?: number
  status: string
  contract: string
  semantic_status: string
  actual_source?: string
  target_source?: string
  scenario?: { id: number; code: string; name: string; status: string }
}

export type SellerRoutesResponse = {
  seller: { personnel_id: number; full_name: string }
  visit_template: string
  routes: SellerRoute[]
  day_route: { id: string; title: string; date?: string; source?: string } | null
  work_calendar?: SellerWorkCalendar | null
  day_route_status: string
  test_all_routes_override?: boolean
  visit_location_policy?: Record<string, unknown>
  source?: string
  live_assignment?: boolean
  detail?: 'basic' | 'full'
}

export type SellerTourBootstrapResponse = {
  routes: SellerRoutesResponse
  route_customers: RouteCustomersResponse | null
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

export type CustomerProfileEditable = {
  phone?: string | null
  national_code?: string | null
  economic_code?: string | null
  store_name?: string | null
  address?: string | null
  mobile?: string | null
  customer_activity_id?: string | null
  state_id?: string | null
  city_id?: string | null
  county_id?: string | null
  city_zone?: number | null
  customer_level_id?: string | null
  customer_category_id?: string | null
  owner_type_ref?: number | null
  postal_code?: string | null
  customer_code?: string | null
  latitude?: number | null
  longitude?: number | null
}

export type CustomerProfileLookupItem = {
  id: string
  title: string
  parent_id?: string
  ref?: number | null
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
    editable?: CustomerProfileEditable
  }
  lookups?: Record<string, CustomerProfileLookupItem[]>
  draft?: CustomerProfileEditable | null
  draft_updated_at?: string | null
  visit_controls?: Record<string, unknown>
  editable_contract?: {
    fields?: string[]
    active_fields?: string[]
    source?: string
    write_mode?: string
  }
}

export type CustomerProfileDraftSaveResponse = {
  route_id: string
  customer_id: string
  draft: CustomerProfileEditable
  updated_at: string
  write_mode: string
  location_available_for_visit: boolean
  message: string
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

function userFacingApiDetail(status: number, detail: string) {
  const clean = repairMojibakeText(detail.trim())
  if (status === 401) return '\u0646\u0634\u0633\u062a \u0634\u0645\u0627 \u0645\u0639\u062a\u0628\u0631 \u0646\u06cc\u0633\u062a. \u062f\u0648\u0628\u0627\u0631\u0647 \u0648\u0627\u0631\u062f \u0634\u0648\u06cc\u062f.'
  if (status === 403) return '\u0628\u0631\u0627\u06cc \u0627\u06cc\u0646 \u0628\u062e\u0634 \u062f\u0633\u062a\u0631\u0633\u06cc \u0644\u0627\u0632\u0645 \u0648\u062c\u0648\u062f \u0646\u062f\u0627\u0631\u062f.'
  if (status >= 500 || /internal server error/i.test(clean)) return '\u0633\u0631\u0648\u06cc\u0633 \u062f\u0627\u062f\u0647 \u0645\u0648\u0642\u062a\u0627\u064b \u062f\u0631 \u062f\u0633\u062a\u0631\u0633 \u0646\u06cc\u0633\u062a. \u062f\u0648\u0628\u0627\u0631\u0647 \u062a\u0644\u0627\u0634 \u06a9\u0646\u06cc\u062f.'
  return clean || `\u062e\u0637\u0627\u06cc \u0627\u0631\u062a\u0628\u0627\u0637\u06cc (${status})`
}

function apiBase() {
  return String(import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '')
}

function apiUrl(path: string) {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${apiBase()}${normalized}`
}

const CP1256_HIGH_BYTES: Record<number, number> = {8364:128,1662:129,8218:130,402:131,8222:132,8230:133,8224:134,8225:135,710:136,8240:137,1657:138,8249:139,338:140,1670:141,1688:142,1672:143,1711:144,8216:145,8217:146,8220:147,8221:148,8226:149,8211:150,8212:151,1705:152,8482:153,1681:154,8250:155,339:156,8204:157,8205:158,1722:159,160:160,1548:161,162:162,163:163,164:164,165:165,166:166,167:167,168:168,169:169,1726:170,171:171,172:172,173:173,174:174,175:175,176:176,177:177,178:178,179:179,180:180,181:181,182:182,183:183,184:184,185:185,1563:186,187:187,188:188,189:189,190:190,1567:191,1729:192,1569:193,1570:194,1571:195,1572:196,1573:197,1574:198,1575:199,1576:200,1577:201,1578:202,1579:203,1580:204,1581:205,1582:206,1583:207,1584:208,1585:209,1586:210,1587:211,1588:212,1589:213,1590:214,215:215,1591:216,1592:217,1593:218,1594:219,1600:220,1601:221,1602:222,1603:223,224:224,1604:225,226:226,1605:227,1606:228,1607:229,1608:230,231:231,232:232,233:233,234:234,235:235,1609:236,1610:237,238:238,239:239,1611:240,1612:241,1613:242,1614:243,244:244,1615:245,1616:246,247:247,1617:248,249:249,1618:250,251:251,252:252,8206:253,8207:254,1746:255}

function cp1256ByteFor(char: string) {
  const codePoint = char.codePointAt(0)
  if (codePoint === undefined) return undefined
  if (codePoint < 128) return codePoint
  return CP1256_HIGH_BYTES[codePoint]
}

function mojibakeScore(value: string) {
  const suspicious = /[\u0637\u0638\u063A\u0622\u0623\u00E2\u0152\u20AC\u00B3\u00B1\u00A2\u2026]/g
  return value.match(suspicious)?.length ?? 0
}

export function repairMojibakeText(value: string) {
  if (mojibakeScore(value) === 0) return value

  let current = value
  for (let pass = 0; pass < 3; pass += 1) {
    const chars = Array.from(current)
    const bytes = new Uint8Array(chars.length)
    let encodable = true

    chars.forEach((char, index) => {
      const byte = cp1256ByteFor(char)
      if (byte === undefined) {
        encodable = false
        return
      }
      bytes[index] = byte
    })

    if (!encodable) break

    let candidate: string
    try {
      candidate = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
    } catch {
      break
    }

    if (candidate === current || mojibakeScore(candidate) >= mojibakeScore(current)) break
    current = candidate
  }

  return current
}

function normalizeApiPayload(value: unknown): unknown {
  if (typeof value === 'string') return repairMojibakeText(value)
  if (Array.isArray(value)) return value.map(normalizeApiPayload)
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, nested]) => [key, normalizeApiPayload(nested)]),
    )
  }
  return value
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

  if (response.status === 401 && !['/auth/login', '/auth/logout', '/auth/me'].includes(path)) {
    window.dispatchEvent(new Event('neginai:auth-expired'))
  }

  if (!response.ok) {
    const detail = typeof payload === 'object' && payload !== null && 'detail' in payload
      ? String((payload as { detail?: unknown }).detail ?? '')
      : typeof payload === 'string'
        ? payload
        : ''
    throw new NeginApiError(response.status, userFacingApiDetail(response.status, detail))
  }

  return normalizeApiPayload(payload) as T
}

export type NotificationSeverity = 'critical' | 'high' | 'medium' | 'info'

export type AutomationNotification = {
  id: number
  automation_id: number | null
  title: string
  body: string
  source: string
  category: string
  severity: NotificationSeverity
  entity_type?: string | null
  entity_id?: string | null
  action_path?: string | null
  requires_ack: boolean
  acknowledged: boolean
  occurred_at: string
  read: boolean
  created_at: string
}

export type AutomationNotificationsResponse = { notifications: AutomationNotification[] }

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
    return request<{ authenticated: false }>('/auth/logout', { method: 'POST', keepalive: true })
  },

  async changePassword(currentPassword: string, newPassword: string) {
    return request<AuthProfile>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    })
  },

  async automationNotifications() {
    return request<AutomationNotificationsResponse>('/automations/notifications?limit=100')
  },

  async markAutomationNotificationsRead(notificationIds: number[]) {
    return request<{ updated: number }>('/automations/notifications/read', {
      method: 'POST',
      body: JSON.stringify({ notification_ids: notificationIds }),
    })
  },

  async acknowledgeAutomationNotifications(notificationIds: number[]) {
    return request<{ updated: number }>('/automations/notifications/acknowledge', {
      method: 'POST',
      body: JSON.stringify({ notification_ids: notificationIds }),
    })
  },

  async routes() {
    return request<SellerRoutesResponse>('/seller-workspace/routes')
  },

  async tourBootstrap() {
    return request<SellerTourBootstrapResponse>('/seller-workspace/tour-bootstrap')
  },

  async targetPulse() {
    return request<SellerTargetPulse>('/seller-workspace/target-pulse')
  },

  async routeCustomers(routeId: string, detail: 'basic' | 'full' = 'basic') {
    return request<RouteCustomersResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers?detail=${detail}`)
  },

  async customerProfile(routeId: string, customerId: string) {
    return request<CustomerProfileResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/profile`)
  },

  async customerProfileAnyRoute(customerId: string) {
    return request<CustomerProfileResponse>(`/seller-workspace/customers/${encodeURIComponent(customerId)}/profile`)
  },

  async saveCustomerProfileDraft(routeId: string, customerId: string, payload: CustomerProfileEditable) {
    return request<CustomerProfileDraftSaveResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/profile-draft`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
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

export type SellerVisitAnalytics = {
  company_invoice_count_12m?: number
  company_net_sales_12m?: number
  last_invoice_date?: string
  seller_invoice_count_12m?: number
  seller_net_sales_12m?: number
  purchased_brands?: Array<Record<string, unknown>>
  line_purchased_brands?: Array<Record<string, unknown>>
  line_purchase_summary?: Array<Record<string, unknown>>
  line_brand_count?: number
  purchased_brand_count?: number
  visit_score?: number
  score_breakdown?: Record<string, number>
}

export type SellerOpenInvoice = {
  id: number
  number: string
  date: string
  amount: number
  remaining_amount: number
}

export type SellerOpenInvoicesResponse = {
  customer_id: string | number
  invoice_count: number
  invoices: SellerOpenInvoice[]
  source: string
}

export type SellerChequeIntelligence = {
  customer_id: string | number
  summary: Record<string, number | undefined>
  cheques: Array<Record<string, unknown>>
  source: string
  classification?: Record<string, string>
}

export type SellerVisitWorkspaceResponse = {
  route: { id: string; title: string }
  customer: CustomerProfileResponse['customer']
  analytics: SellerVisitAnalytics
  open_invoices: SellerOpenInvoicesResponse
  cheques: SellerChequeIntelligence
  sources: Record<string, unknown>
  read_only: boolean
}

export type SellerVisitReason = {
  id: string
  title: string
  type_id?: string
}

export type SellerVisitPolicyResponse = {
  route: { id: string; title: string }
  customer: {
    id: string | number
    name?: string
    store_name?: string
    has_location: boolean
    location_check_exempt: boolean
  }
  controls: {
    enabled?: boolean
    enforced?: boolean
    max_distance_meters?: number | null
    mode?: string
    [key: string]: unknown
  }
  missing_required_fields: string[]
  start_blockers: string[]
  order_blockers: string[]
  can_start_visit: boolean
  reasons: Record<string, SellerVisitReason[]>
  visit_status_ids: Record<string, string | null>
  source: string
}

export type PrevisitDraftLine = {
  product_id: string
  quantity: number
  unit_price: number
  discount_amount: number
  title: string
}

export type PrevisitVisitDraftResponse = {
  visit_id: string
  route_id: string
  customer_id: string
  visit_status: string
  started_at: string
  idempotency_key: string
  warehouse_ref: number | null
  warehouse_name: string
  lines: PrevisitDraftLine[]
  line_count: number
  total_amount: number
  payment_type: string
  order_type: string
  outcome: string
  outcome_reason: string
  outcome_reason_id: string | null
  visit_status_id: string | null
  start_distance_meters: number | null
  ngt_send_enabled: boolean
  ngt_status: string
}

export type PrevisitVisitStartPayload = {
  route_id: string
  customer_id: string
  latitude?: number | null
  longitude?: number | null
  accuracy?: number | null
}

export type PrevisitOutcomePayload = {
  outcome: 'order' | 'no_order' | 'no_visit' | 'skipped'
  reason_id?: string | null
  reason?: string
  latitude?: number | null
  longitude?: number | null
  accuracy?: number | null
}

export type PrevisitDraftUpdatePayload = {
  lines: PrevisitDraftLine[]
  payment_type: string
  order_type: string
  warehouse_ref?: number | null
  warehouse_name: string
}

export async function getVisitWorkspace(routeId: string, customerId: string) {
  return request<SellerVisitWorkspaceResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/customers/${encodeURIComponent(customerId)}/visit-workspace`)
}

export async function getVisitPolicy(routeId: string, customerId: string) {
  const params = new URLSearchParams({ path_id: routeId, customer_id: customerId })
  return request<SellerVisitPolicyResponse>(`/seller-workspace/previsit/policy?${params}`)
}

export async function startServerVisit(payload: PrevisitVisitStartPayload) {
  return request<PrevisitVisitDraftResponse>('/seller-workspace/previsit/visits', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getVisitDraft(visitId: string) {
  return request<PrevisitVisitDraftResponse>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}`)
}

export async function updateVisitDraft(visitId: string, payload: PrevisitDraftUpdatePayload) {
  return request<PrevisitVisitDraftResponse>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/draft`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function completeServerVisit(visitId: string, payload: PrevisitOutcomePayload) {
  return request<PrevisitVisitDraftResponse>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/complete`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
export type NeshanMapConfigResponse = Record<string, string>
export type NeshanRouteMetric = { text?: string; value?: number; [key: string]: unknown }
export type NeshanRouteStep = { instruction?: string; distance?: NeshanRouteMetric; duration?: NeshanRouteMetric; start_location?: number[]; [key: string]: unknown }
export type NeshanRouteLeg = { distance?: NeshanRouteMetric; duration?: NeshanRouteMetric; steps?: NeshanRouteStep[]; [key: string]: unknown }
export type NeshanRouteMapCustomer = SellerCustomer & { visit_score: number; analysis: Record<string, unknown>; priority_tier: string }
export type NeshanRouteMapPlanResponse = { route: { id: string; title: string }; customers: NeshanRouteMapCustomer[]; missing_location_count: number; ordered_customers: NeshanRouteMapCustomer[]; unlocated_customers: NeshanRouteMapCustomer[]; has_origin?: boolean; polyline: string; legs: NeshanRouteLeg[]; initial_leg: NeshanRouteLeg | null; route_mode: string; visit_location_policy: Record<string, unknown>; analytics_available: boolean }
export type NeshanRouteMapLegResponse = { polyline: string; leg: NeshanRouteLeg | null }

export async function getNeshanMapConfig() { return request<NeshanMapConfigResponse>('/seller-workspace/map-config') }
export async function getRouteMapPlan(routeId: string, routeMode: 'sales_priority' | 'shortest', origin?: { latitude: number; longitude: number } | null) {
  const params = new URLSearchParams({ route_mode: routeMode, start_day_route: 'false' })
  if (origin) { params.set('origin_latitude', String(origin.latitude)); params.set('origin_longitude', String(origin.longitude)) }
  return request<NeshanRouteMapPlanResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/map-plan?${params}`)
}
export async function getRouteMapLeg(routeId: string, customerId: string, origin: { latitude: number; longitude: number }) {
  const params = new URLSearchParams({ destination_id: customerId, origin_latitude: String(origin.latitude), origin_longitude: String(origin.longitude) })
  return request<NeshanRouteMapLegResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/map-leg?${params}`)
}


export type SellerPortfolioOpenInvoiceCustomer = {
  id: string | number
  code: string
  name: string
  store_name: string
  address: string
  phone: string
  mobile: string
  return_cheque_count: number
  return_cheque_amount: number
  cardex_balance: number
  open_invoice_remaining: number
  open_invoice_count: number
  oldest_open_invoice_date: string
}

export type SellerPortfolioOpenInvoicesResponse = {
  seller: { personnel_id: number; full_name: string }
  customer_count: number
  open_invoice_remaining: number
  customers: SellerPortfolioOpenInvoiceCustomer[]
  source: string
  live_assignment: boolean
}

export type SellerPortfolioReturnedCheque = {
  id: number
  number: string
  date: string
  amount: number
  bank: string
  branch: string
  customer_id: number | null
  customer_code: string
  customer_name: string
  customer_store: string
  account_name: string
  customer_phone: string
  customer_mobile: string
  status: string
  status_date: string
  seller_share: number
  settled_amount: number
}

export type SellerPortfolioReturnedChequesResponse = {
  seller: { personnel_id: number; full_name: string }
  cheque_count: number
  cheque_amount: number
  seller_share: number
  settled_amount: number
  cheques: SellerPortfolioReturnedCheque[]
  source: string
}

export type SellerDistributionInvoice = {
  id: number
  number: string
  sale_date: string
  amount: number
  customer_code: string
  customer_name: string
  customer_store: string
  distribution_number: string
  distribution_date: string
  sent_at: string
  driver_name: string
  driver_mobile: string
}

export type SellerDistributionInProgressResponse = {
  seller: { personnel_id: number; full_name: string }
  distribution_date: string
  distribution_dates: string[]
  invoice_count: number
  invoices: SellerDistributionInvoice[]
  source: string
}

export type SellerVoucherReturnReportResponse = {
  seller: { personnel_id: number; full_name: string }
  report_month: string
  voucher_count: number
  invoiced_count: number
  full_returned_count: number
  undistributed_count: number
  returned_count: number
  reconciled_voucher_count: number
  return_percentage: number
  source: string
}

export type RouteSavedRequest = {
  id: string
  visit_id: string
  route_id: string
  customer_id: string
  request_number: number
  lines: Array<Record<string, unknown>>
  line_count: number
  total_amount: number
  payment_type: string
  order_type: string
  warehouse_ref: number | null
  warehouse_name: string
  preview: Record<string, unknown>
  created_at: string
  updated_at: string
}

export type RouteSavedRequestsResponse = { requests: RouteSavedRequest[] }

export async function getRouteSavedRequests(routeId: string) {
  return request<RouteSavedRequestsResponse>(`/seller-workspace/routes/${encodeURIComponent(routeId)}/saved-requests`)
}

export async function getSellerPortfolioOpenInvoices() {
  return request<SellerPortfolioOpenInvoicesResponse>('/seller-workspace/open-invoices')
}

export async function getSellerPortfolioReturnedCheques() {
  return request<SellerPortfolioReturnedChequesResponse>('/seller-workspace/returned-cheques')
}

export async function getSellerDistributionInProgress() {
  return request<SellerDistributionInProgressResponse>('/seller-workspace/distribution-in-progress')
}

export async function getSellerVoucherReturnReport() {
  return request<SellerVoucherReturnReportResponse>('/seller-workspace/voucher-return-report')
}

export type PrevisitProduct = {
  id: string
  code: string
  name: string
  brand: string
  group_id: string
  group: string
  unit: string
  sale_units: Array<{ ref: number | null; name: string; factor: number; is_default: boolean }>
  available_qty: number
  carton_size: number
  min_order_qty: number
  max_order_qty: number
  indicative_price: number
  consumer_price: number
  indicative_prices: Record<string, number>
  warehouse_inventory: Record<string, { on_hand_qty: number; reserved_qty: number; available_qty: number }>
}

export type PrevisitContextResponse = {
  route: { id: string; title: string }
  customer: SellerCustomer
  order_types: Array<{ id: number; name: string }>
  payment_types: Array<{ id: string; name: string; is_cash: boolean; check_credit: boolean; check_debit: boolean }>
  warehouses: Array<{ id: string; ref: number; name: string; dc_ref: number }>
  warehouse_selection: { enabled: boolean; default_ref: number; source: string }
  products: PrevisitProduct[]
  grouped_catalogs: Array<{ id: string; name: string; image_url: string; product_ids: string[]; brands: string[]; group_ids: string[] }>
  catalog_filters: { brands: string[]; groups: Array<{ id: string; name: string }> }
  inventory: { show_stock_level: boolean; source: string }
  preview: { available: boolean; authoritative: boolean; creates_order: boolean }
  browse_only?: boolean
}

export type PrevisitPreviewRequestPayload = {
  route_id: string
  customer_id: string
  order_type_ref: number
  payment_usance_ref: string
  warehouse_ref?: number | null
  lines: Array<{ product_id: string; quantity: number }>
}

export type PrevisitDiscountPart = { amount: number; percent: number }
export type PrevisitDiscountBreakdown = {
  cash: PrevisitDiscountPart
  volume: PrevisitDiscountPart
  goods: PrevisitDiscountPart
  other: PrevisitDiscountPart
  unclassified: PrevisitDiscountPart
}
export type PrevisitGiftLine = {
  product_id: string
  parent_product_id: string
  title: string
  quantity: number
  unit_price: number
  gross_amount: number
  discount_amount: number
  discount_percent: number
  net_amount: number
  source: string
}
export type PrevisitCreditControl = {
  allowed?: boolean
  blocking?: boolean
  mode?: string
  mode_label?: string
  message?: string
  current_order_amount?: number
  pending_ngt_order_amount?: number
  evaluated_total?: number
  available_amount?: number | null
  deficit?: number
  financials?: {
    customer_remaining?: number
    open_invoice_count?: number
    open_invoice_amount?: number
    open_cheque_count?: number
    open_cheque_amount?: number
    returned_cheque_count?: number
    returned_cheque_amount?: number
  }
  [key: string]: unknown
}
export type PrevisitPreviewResponse = {
  ok: boolean
  message: string
  items: Array<{
    product_id: string
    quantity: number
    unit_price: number
    discount_amount: number
    discount_percent: number
    discount_breakdown?: PrevisitDiscountBreakdown
    gross_amount: number
    tax_amount: number
    charge_amount: number
    tax_and_charge_amount?: number
    net_amount: number
    rule_no: string
  }>
  totals: { gross: number; discount: number; tax: number; charge: number; net: number }
  gift_lines: PrevisitGiftLine[]
  restrictions: unknown[]
  source: string
  creates_order: false
  credit_control?: PrevisitCreditControl
  order_type?: { id: number; name: string }
  payment_type?: { id: string; name: string }
  warehouse?: { id: string; ref: number; name: string } | null
}

export type PrevisitSavedRequestPayload = {
  lines: PrevisitDraftLine[]
  payment_type: string
  order_type: string
  warehouse_ref?: number | null
  warehouse_name: string
  preview: Record<string, unknown>
}

export async function getPrevisitContext(routeId: string, customerId: string, search = '', limit = 1000) {
  const params = new URLSearchParams({ path_id: routeId, customer_id: customerId, search, limit: String(limit) })
  return request<PrevisitContextResponse>(`/seller-workspace/previsit/context?${params}`)
}

export async function getPrevisitBrowseContext(routeId: string, customerId: string, search = '', limit = 1000) {
  const params = new URLSearchParams({ path_id: routeId, customer_id: customerId, search, limit: String(limit) })
  return request<PrevisitContextResponse>(`/seller-workspace/previsit/browse-context?${params}`)
}

export async function previewPrevisit(payload: PrevisitPreviewRequestPayload) {
  return request<PrevisitPreviewResponse>('/seller-workspace/previsit/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function createSavedPrevisitRequest(visitId: string, payload: PrevisitSavedRequestPayload) {
  return request<RouteSavedRequest>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/saved-requests`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getVisitSavedRequests(visitId: string) {
  return request<RouteSavedRequestsResponse>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/saved-requests`)
}

export async function getSavedPrevisitRequest(visitId: string, requestId: string) {
  return request<RouteSavedRequest>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/saved-requests/${encodeURIComponent(requestId)}`)
}

export async function updateSavedPrevisitRequest(visitId: string, requestId: string, payload: PrevisitSavedRequestPayload) {
  return request<RouteSavedRequest>(`/seller-workspace/previsit/visits/${encodeURIComponent(visitId)}/saved-requests/${encodeURIComponent(requestId)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}