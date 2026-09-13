export type SellerRoute = {
  id: string
  title: string
  row_index?: number | null
  updated_at?: string
  customer_count: number
  source?: string
  is_day_route: boolean
  can_start_day_route: boolean
  can_start_visit: boolean
}

export type SellerRoutesResponse = {
  seller?: { personnel_id?: number; full_name?: string }
  visit_template?: string
  routes: SellerRoute[]
  day_route?: { id?: string; title?: string; date?: string; source?: string; [key: string]: unknown } | null
  day_route_status?: 'assigned' | 'not_assigned' | 'temporary_all_routes' | string
  test_all_routes_override?: boolean
  visit_location_policy?: Record<string, unknown>
  source?: string
  live_assignment?: boolean
}

export type VisitResolution = {
  status?: string
  outcome?: string
  outcome_reason?: string
  saved_request_count?: number
  ended_at?: string
}

export type SellerCustomer = {
  id: string | number
  code?: string
  name?: string
  store_name?: string
  address?: string
  latitude?: number | null
  longitude?: number | null
  location_source?: string
  location_check_exempt?: boolean
  phone?: string
  mobile?: string
  visit_resolution?: VisitResolution | null
  cardex_balance?: number
  open_invoice_remaining?: number
  open_invoice_count?: number
  financial_snapshot?: Record<string, unknown>
}

export type SellerRouteCustomersResponse = {
  route: { id: string; title: string }
  customer_count: number
  customers: SellerCustomer[]
  visit_location_policy?: Record<string, unknown>
  source?: string
  live_assignment?: boolean
}

export function routeQueryValue(name: 'pathId' | 'customerId') {
  return new URLSearchParams(window.location.search).get(name)?.trim() ?? ''
}

export function isReviewMode() {
  return import.meta.env.DEV && new URLSearchParams(window.location.search).get('review') === '1'
}

export function customerDisplayName(customer: SellerCustomer) {
  return customer.store_name || customer.name || String(customer.id)
}

export function visitStatusLabel(customer: SellerCustomer) {
  const resolution = customer.visit_resolution
  if (!resolution || resolution.status !== 'completed') return 'در انتظار'
  if (resolution.outcome === 'order') return 'سفارش ثبت‌شده'
  if (resolution.outcome === 'no_order') return 'بدون سفارش'
  if (resolution.outcome === 'no_visit') return 'عدم ویزیت'
  if (resolution.outcome === 'skipped') return 'رد شده'
  return 'تکمیل‌شده'
}

export type SellerFinancialSnapshot = {
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

export type SellerCustomerProfile = SellerCustomer & {
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
  financial_snapshot?: SellerFinancialSnapshot
}

export type SellerCustomerProfileResponse = {
  route: { id: string; title: string }
  customer: SellerCustomerProfile
  lookups: Record<string, Array<Record<string, unknown>>>
  draft: Record<string, unknown> | null
  draft_updated_at: string | null
  visit_controls: Record<string, unknown>
  editable_contract: {
    fields: string[]
    active_fields: string[]
    source: string
    write_mode: string
  }
}
