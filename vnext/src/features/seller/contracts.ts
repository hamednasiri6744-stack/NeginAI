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

export function routeQueryValue(name: 'pathId' | 'customerId' | 'visitId' | 'requestId') {
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

export type SellerChequeSummary = {
  paid_12m_count?: number
  paid_12m_amount?: number
  active_returned_count?: number
  active_returned_amount?: number
  collected_after_return_count?: number
  collected_after_return_amount?: number
  refunded_after_return_count?: number
  refunded_after_return_amount?: number
  legal_returned_count?: number
  legal_returned_amount?: number
  fully_settled_returned_count?: number
  returned_settlement_amount?: number
}

export type SellerChequeIntelligence = {
  customer_id: string | number
  summary: SellerChequeSummary
  cheques: Array<Record<string, unknown>>
  source: string
  classification?: Record<string, string>
}

export type SellerVisitWorkspaceResponse = {
  route: { id: string; title: string }
  customer: SellerCustomerProfile
  analytics: SellerVisitAnalytics
  open_invoices: SellerOpenInvoicesResponse
  cheques: SellerChequeIntelligence
  sources: Record<string, unknown>
  read_only: boolean
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
  reasons?: Record<string, Array<Record<string, unknown>>>
  visit_status_ids?: Record<string, string | null>
  source: string
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

export type PrevisitOrderType = {
  id: number
  name: string
}

export type PrevisitPaymentType = {
  id: string
  name: string
  buy_type_ref: number
  payment_deadline?: number
  payment_time?: number
  is_cash?: boolean
  check_credit?: boolean
  check_debit?: boolean
}

export type PrevisitWarehouse = {
  id: string
  ref: number
  name: string
  dc_ref?: number
}

export type PrevisitWarehouseInventory = {
  on_hand_qty?: number
  reserved_qty?: number
  available_qty?: number
}

export type PrevisitProduct = {
  id: string
  unique_id?: string
  code?: string
  name: string
  brand?: string
  barcode?: string
  description?: string
  group_id?: string
  group?: string
  group_parent_id?: string
  group_parent?: string
  smallest_group_id?: string
  smallest_group?: string
  manufacturer?: string
  stock_name?: string
  stock_unique_id?: string
  stock_ref?: string
  unit?: string
  sale_units?: Array<Record<string, unknown>>
  on_hand_qty?: number
  reserved_qty?: number
  available_qty?: number
  carton_size?: number
  min_order_qty?: number
  max_order_qty?: number
  tax_percent?: number
  charge_percent?: number
  indicative_price?: number
  consumer_price?: number
  manufacturer_price?: number
  catalog_tax_percent?: number
  catalog_tax_inclusive_price?: number
  indicative_order_type_ref?: number
  indicative_prices?: Record<string, number>
  consumer_prices?: Record<string, number>
  manufacturer_prices?: Record<string, number>
  warehouse_inventory?: Record<string, PrevisitWarehouseInventory>
}

export type PrevisitContextResponse = {
  seller: { personnel_id: number; full_name: string }
  route: { id: string; title: string }
  customer: SellerCustomer
  order_types: PrevisitOrderType[]
  payment_types: PrevisitPaymentType[]
  warehouses: PrevisitWarehouse[]
  warehouse_selection: {
    enabled: boolean
    default_ref: number
    source: string
  }
  products: PrevisitProduct[]
  grouped_catalogs: Array<Record<string, unknown>>
  grouped_catalog_count: number
  catalog_count: number
  catalog_filters: {
    brands: string[]
    groups: Array<{ id: string; name: string }>
  }
  inventory: {
    show_stock_level: boolean
    online_refresh: boolean
    applies_current_orders: boolean
    source: string
  }
  preview: {
    available: boolean
    authoritative: boolean
    creates_order: boolean
  }
  pricing: {
    catalog_kind: string
    catalog_order_type_ref: number
    catalog_cache_seconds: number
    official_preview_depends_on: string[]
    official_source: string
  }
  credit_control: {
    checked_on_registration: boolean
    advanced_control: boolean
    allow_cash_without_advanced_control: boolean
    source: string
  }
}

export type PrevisitDraftLine = {
  product_id: string
  quantity: number
  unit_price: number
  discount_amount: number
  title: string
}


export type PrevisitPreviewItem = {
  product_id: string
  quantity: number
  unit_price: number
  discount_amount: number
  discount_percent?: number
  discount_breakdown?: Record<string, { amount?: number; percent?: number }>
  gross_amount: number
  tax_amount: number
  charge_amount: number
  tax_and_charge_amount: number
  net_amount: number
  rule_no?: string
}

export type PrevisitPreviewTotals = {
  gross: number
  discount: number
  tax: number
  charge: number
  net: number
}

export type PrevisitCreditControl = {
  allowed: boolean
  blocking?: boolean
  mode?: string
  mode_label?: string
  message?: string
  current_order_amount?: number
  pending_ngt_order_amount?: number
  evaluated_total?: number
  available_amount?: number | null
  deficit?: number
}

export type PrevisitGiftLine = {
  product_id: string
  parent_product_id?: string
  title?: string
  quantity: number
  unit_price?: number
  gross_amount?: number
  discount_amount?: number
  discount_percent?: number
  net_amount?: number
  source?: string
}

export type PrevisitPreviewResponse = {
  ok: boolean
  error_code?: unknown
  message?: string
  evc_id?: unknown
  items: PrevisitPreviewItem[]
  totals: PrevisitPreviewTotals
  prizes?: unknown[]
  gift_lines?: PrevisitGiftLine[]
  restrictions?: unknown[]
  related_rules?: Array<Record<string, unknown>>
  payment?: Record<string, unknown>
  order_type?: PrevisitOrderType
  payment_type?: PrevisitPaymentType
  warehouse?: PrevisitWarehouse | null
  credit_control: PrevisitCreditControl
  source?: string
  creates_order: boolean
}

export type PrevisitSavedRequest = {
  id: string
  visit_id: string
  route_id: string
  customer_id: string
  request_number: number
  lines: PrevisitDraftLine[]
  line_count: number
  total_amount: number
  payment_type: string
  order_type: string
  warehouse_ref: number | null
  warehouse_name: string
  preview: PrevisitPreviewResponse | Record<string, unknown>
  created_at: string
  updated_at: string
}

export type PrevisitSavedRequestsResponse = {
  requests: PrevisitSavedRequest[]
}
