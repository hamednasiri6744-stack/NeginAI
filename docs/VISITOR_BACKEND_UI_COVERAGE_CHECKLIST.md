# NeginAI Visitor â€” Backend/UI Coverage Checklist

Canonical tracking file for what the current Visitor app actually uses from Backend/NGT/Varanegar inventory.

Last audit: 2026-09-19
Branch: feature/layout-architecture-migration-20260918
Rule: [x] means the current frontend consumes/displays/uses it. [ ] means backend/inventory capability exists but is not yet surfaced or completed in the Visitor UI.
Semantic rule: a checked UI item does not make an unvalidated KPI canonical. Semantic status is tracked explicitly.

Current snapshot: 131/180 tracked rows checked; 49 remaining. Exact Seller API coverage: 26/32 endpoints connected; 6 remaining.

## 1) Authentication / account
- [x] Login â€” POST /auth/login
- [x] Session restore / current user â€” GET /auth/me
- [x] Logout â€” POST /auth/logout
- [x] Change password â€” POST /auth/change-password
- [ ] Account activation flow â€” POST /auth/activate
- [x] Seller identity / personnel / branch / sales line / permissions
- [x] Profile screen entry from header

## 2) Home / daily pulse
- [x] Persian date
- [x] Tehran time
- [x] Day of week
- [x] Total working days of month from NGT calendar
- [x] Elapsed working days
- [x] Remaining working days
- [x] Monthly sales target UI slot
- [x] Monthly actual sales UI slot
- [x] Monthly achievement percentage + circular progress
- [x] Monthly remaining-to-target
- [x] Target-to-today UI slot
- [x] Actual sales-to-today UI slot
- [x] Achievement-to-today percentage + circular progress
- [x] Remaining target-to-today
- [x] Total sales still required to reach 100%
- [x] Daily required sales across remaining working days
- [x] GET /seller-workspace/target-pulse wired to Home
- [ ] Target semantic contract validation â€” current backend status: NEEDS_VALIDATION
- [ ] Approved/locked target value for test seller when planning target is not configured
- [ ] Remaining Home stage-2 sections â€” intentionally waiting for layout instruction

## 3) Notifications / live events
- [x] Notification list â€” GET /automations/notifications
- [x] Mark read â€” POST /automations/notifications/read
- [x] Acknowledge â€” POST /automations/notifications/acknowledge
- [x] Live seller event stream â€” GET /seller-workspace/live-events
- [x] Notification badge in header
- [x] Notification screen/categories
- [ ] Push status UI â€” GET /push/status
- [ ] Push subscribe/unsubscribe UI â€” /push/subscriptions
- [ ] Push test UI â€” POST /push/test

## 4) Routes / map / field execution
- [x] Assigned routes â€” GET /seller-workspace/routes
- [x] Day-route / live assignment
- [x] Route customers â€” GET /seller-workspace/routes/{path_id}/customers
- [x] Basic/full customer detail modes
- [x] Neshan map config â€” GET /seller-workspace/map-config
- [x] Route map plan â€” GET /seller-workspace/routes/{path_id}/map-plan
- [x] Route map leg â€” GET /seller-workspace/routes/{path_id}/map-leg
- [x] Current GPS origin support
- [x] Customer geo destination
- [x] Sales-priority route mode
- [x] Visit-location policy is read from backend/NGT
- [ ] GRS connector exposed in current NeginAI backend
- [ ] Route discovery from GRS as a first-class UI source

## 5) Customers / Customer 360
- [x] Customer list by route
- [x] Full customer list financial signals
- [x] Customer profile in route â€” GET .../customers/{customer_id}/profile
- [x] Customer profile independent of active route â€” GET /customers/{customer_id}/profile
- [x] Customer editable draft â€” PUT .../profile-draft
- [x] Dynamic editable fields contract
- [x] Customer phone action
- [x] Customer geo/navigation action
- [x] Visit count
- [x] Order count
- [x] Open-invoice count / balance signals
- [x] Returned-cheque risk signals
- [x] Customer financial snapshot
- [x] Visit workspace â€” GET .../visit-workspace
- [ ] Dedicated customer open-invoices endpoint UI â€” GET /open-invoices/{customer_id}

## 6) Visit / NGT workflow
- [x] Visit policy â€” GET /previsit/policy
- [x] Start visit â€” POST /previsit/visits
- [x] Read active visit â€” GET /previsit/visits/{visit_id}
- [x] Save visit/order draft â€” PUT /previsit/visits/{visit_id}/draft
- [x] Complete visit â€” POST /previsit/visits/{visit_id}/complete
- [x] Outcome workflow: Order
- [x] Outcome workflow: No Order
- [x] Outcome workflow: No Visit
- [x] NGT reason-based completion path
- [x] Route/customer ownership restrictions enforced by backend
- [x] Duplicate active-visit protection handled by backend
- [ ] Previsit warmup â€” POST /previsit/warmup
- [ ] Distance enforcement at visit start â€” backend switch currently disabled

## 7) Orders / catalog / pricing / incentives
- [x] Operational previsit context â€” GET /previsit/context
- [x] Browse-only context â€” GET /previsit/browse-context
- [x] Product catalog
- [x] Grouped NGT catalogs
- [x] Catalog/product images
- [x] Brand filter from previsit context
- [x] Product-group filter
- [x] Search
- [x] Warehouse selection
- [x] Warehouse-specific available quantity
- [x] On-hand/reserved/available semantics consumed from backend context
- [x] Order type selection
- [x] Payment type selection
- [x] Sale units / unit factor selection
- [x] Min order quantity
- [x] Max order quantity
- [x] Indicative price for browsing/cart estimate
- [x] Official NGT/EVC preview â€” POST /previsit/preview
- [x] Official gross/discount/tax/charge/net totals
- [x] Official discount breakdown
- [x] Credit control result/blocking
- [x] Official gift/prize lines
- [x] Official restrictions returned from EVC
- [x] Server draft autosave
- [x] Create saved request â€” POST .../saved-requests
- [x] Route saved-request archive â€” GET /routes/{route}/saved-requests
- [ ] Visit saved-request list â€” GET /visits/{visit}/saved-requests
- [ ] Open individual saved request â€” GET .../saved-requests/{request_id}
- [ ] Update individual saved request â€” PUT .../saved-requests/{request_id}
- [ ] Direct /seller-workspace/brands endpoint in UI (brands currently arrive through previsit context)
- [ ] Varanegar final order bridge enabled
- [ ] Varanegar order commit enabled
- [ ] Varanegar order numbering verified
- [ ] Prize-order commit mapping completed
- [ ] Durable command outbox enabled

## 8) Reports / financial operational data
- [x] Portfolio open invoices â€” GET /seller-workspace/open-invoices
- [x] Returned cheques â€” GET /seller-workspace/returned-cheques
- [x] Distribution in progress â€” GET /seller-workspace/distribution-in-progress
- [x] Voucher/return report â€” GET /seller-workspace/voucher-return-report
- [x] Receivables drill-down in Reports
- [x] Returned-cheque drill-down in Reports
- [x] Distribution drill-down in Reports
- [x] Return/voucher drill-down in Reports
- [ ] Separate customer-specific open-invoice detail UI

## 9) AI assistant
- [x] Basic chat request â€” POST /chat
- [x] AI screen entry
- [ ] Conversation list/history UI
- [ ] Conversation messages/history UI
- [ ] Delete/rename conversation UI
- [ ] Excel export from conversation
- [ ] Attachment analysis UI
- [ ] Audio transcription UI
- [ ] Navigation speech/TTS UI
- [ ] Schema catalog UI
## 10) Backend capabilities intentionally not exposed in Visitor UI yet
- [ ] Planning scenario management UI
- [ ] Organization-structure management UI
- [ ] Direct SQL query UI â€” should remain admin/data-only
- [ ] Schema/metadata administration UI
- [ ] Automation create/pause/resume/delete UI
- [ ] Warehouse Assistant modules â€” separate product/domain
- [ ] Supplier Portal modules â€” separate product/domain

## 11) Current external/data connections relevant to Visitor
- [x] SQL Server / NeginPakhsh read-only reporting path
- [x] NGT data/contracts used by seller workspace
- [x] Neshan Web/Service integration
- [x] Local operational state used by app/backend
- [ ] NGT HTTP/EVC remote base credentials configured in current runtime
- [ ] Varanegar write bridge enabled
- [ ] GRS DB wired as official current backend connector
- [ ] VNDBBACK wired as current Visitor backend connector
- [ ] Redis configured
- [ ] Enterprise PostgreSQL store configured

## 12) Exact Seller API endpoint coverage
- [ ] GET /seller-workspace/brands
- [x] GET /seller-workspace/customers/{customer_id}/profile
- [x] GET /seller-workspace/distribution-in-progress
- [x] GET /seller-workspace/live-events
- [x] GET /seller-workspace/map-config
- [x] GET /seller-workspace/open-invoices
- [ ] GET /seller-workspace/open-invoices/{customer_id}
- [x] GET /seller-workspace/previsit/browse-context
- [x] GET /seller-workspace/previsit/catalog-images/{catalog_id}/{image_name} (consumed through image_url)
- [x] GET /seller-workspace/previsit/context
- [x] GET /seller-workspace/previsit/policy
- [x] POST /seller-workspace/previsit/preview
- [x] POST /seller-workspace/previsit/visits
- [x] GET /seller-workspace/previsit/visits/{visit_id}
- [x] POST /seller-workspace/previsit/visits/{visit_id}/complete
- [x] PUT /seller-workspace/previsit/visits/{visit_id}/draft
- [ ] GET /seller-workspace/previsit/visits/{visit_id}/saved-requests
- [x] POST /seller-workspace/previsit/visits/{visit_id}/saved-requests
- [ ] GET /seller-workspace/previsit/visits/{visit_id}/saved-requests/{request_id}
- [ ] PUT /seller-workspace/previsit/visits/{visit_id}/saved-requests/{request_id}
- [ ] POST /seller-workspace/previsit/warmup
- [x] GET /seller-workspace/returned-cheques
- [x] GET /seller-workspace/routes
- [x] GET /seller-workspace/routes/{path_id}/customers
- [x] GET /seller-workspace/routes/{path_id}/customers/{customer_id}/profile
- [x] PUT /seller-workspace/routes/{path_id}/customers/{customer_id}/profile-draft
- [x] GET /seller-workspace/routes/{path_id}/customers/{customer_id}/visit-workspace
- [x] GET /seller-workspace/routes/{path_id}/map-leg
- [x] GET /seller-workspace/routes/{path_id}/map-plan
- [x] GET /seller-workspace/routes/{path_id}/saved-requests
- [x] GET /seller-workspace/target-pulse
- [x] GET /seller-workspace/voucher-return-report

## Maintenance rule
Whenever a backend capability is connected to a real screen/interaction, change its checkbox to [x] in this file in the same commit. Never tick an item only because an endpoint exists. For KPI/financial/Varanegar items, keep semantic validation status separate from UI wiring.
