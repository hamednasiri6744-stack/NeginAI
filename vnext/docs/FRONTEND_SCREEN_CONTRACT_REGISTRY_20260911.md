# NeginAI vNext — Frontend Screen Contract Registry

**Generated:** 2026-09-11  
**Branch:** `dev/hamed`  
**Frontend root:** `D:\Projects\NeginAI\vnext`  
**Evidence:** static repository inspection only; E2E runtime verification is still pending.

## Rules

- `vnext` is the active modern frontend target. `app/static` is a legacy behavior / feature-parity source, not the target UI implementation.
- `WIRED_STATIC_VERIFIED` means source-level API wiring was observed; it does **not** mean end-to-end acceptance has passed.
- Business KPI/report semantics remain subject to the approved Negin Pakhsh / Varanegar Semantic Source. Raw table/view totals are not canonical KPIs.
- No destructive operation, file move, service restart, SQL DML/DDL, or production write is authorized by this registry.

## Current gap summary

- **WIRED_STATIC_VERIFIED:** 2
- **PARTIAL:** 3
- **PRESENTATION_ONLY:** 2
- **MISSING_UI_BACKEND_READY:** 23
- **PRESENTATION_ONLY_NEEDS_SEMANTIC_VALIDATION:** 1
- **Total contracted surfaces:** 31

## Contract table

| ID | Surface | vNext route | Status | Priority | Backend contract |
|---|---|---|---|---|---|
| `SCR-AUTH-LOGIN` | Login / Session Gate | `auth-gate` | **WIRED_STATIC_VERIFIED** | P0 | `/auth/me`<br>`/auth/login`<br>`/auth/logout` |
| `SCR-SHELL-001` | App Shell / Primary Navigation | `global` | **PARTIAL** | P0 | — |
| `SCR-HOME-001` | Home Dashboard | `/` | **PRESENTATION_ONLY** | P0 | `/dashboard/stats (API-key guarded; session parity NEEDS_VALIDATION)` |
| `SCR-MODULES-001` | Modules Hub | `/modules` | **PARTIAL** | P0 | — |
| `SCR-SELLER-ROUTES` | Seller / My Routes | `/seller/routes` | **WIRED_STATIC_VERIFIED** | P0 | `GET /seller-workspace/routes` |
| `SCR-SELLER-CUSTOMERS` | Route Customers | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `GET /seller-workspace/routes/{path_id}/customers` |
| `SCR-CUSTOMER-PROFILE` | Customer Profile / Customer 360 | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `GET /seller-workspace/routes/{path_id}/customers/{customer_id}/profile`<br>`PUT /seller-workspace/routes/{path_id}/customers/{customer_id}/profile-draft` |
| `SCR-VISIT-WORKSPACE` | Customer Visit Workspace | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `GET /seller-workspace/routes/{path_id}/customers/{customer_id}/visit-workspace` |
| `SCR-ORDER-WORKSPACE` | Previsit / Order Workspace | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `POST /seller-workspace/previsit/visits`<br>`GET /seller-workspace/previsit/policy`<br>`GET /seller-workspace/previsit/context`<br>`POST /seller-workspace/previsit/preview`<br>`PUT /seller-workspace/previsit/visits/{visit_id}/draft`<br>`POST /seller-workspace/previsit/visits/{visit_id}/complete` |
| `SCR-SAVED-REQUESTS` | Saved Requests | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `GET/POST /seller-workspace/previsit/visits/{visit_id}/saved-requests`<br>`GET/PUT /seller-workspace/previsit/visits/{visit_id}/saved-requests/{request_id}`<br>`GET /seller-workspace/routes/{path_id}/saved-requests` |
| `SCR-ROUTE-MAP` | Day Route Map / Navigation | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `GET /seller-workspace/map-config`<br>`GET /seller-workspace/routes/{path_id}/map-plan`<br>`GET /seller-workspace/routes/{path_id}/map-leg`<br>`POST /audio/navigation-speech` |
| `SCR-SELLER-INVOICES` | Open Invoices | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `GET /seller-workspace/open-invoices`<br>`GET /seller-workspace/open-invoices/{customer_id}` |
| `SCR-SELLER-DISTRIBUTION` | Distribution In Progress | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `GET /seller-workspace/distribution-in-progress` |
| `SCR-SELLER-CHEQUES` | Returned Cheques | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `GET /seller-workspace/returned-cheques` |
| `SCR-SELLER-RETURNS` | Voucher / Return Report | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `GET /seller-workspace/voucher-return-report` |
| `SCR-SELLER-BRANDS` | My Brands | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `GET /seller-workspace/brands` |
| `SCR-NOTIFICATIONS` | Notifications Center | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `GET /automations/notifications`<br>`POST /automations/notifications/read` |
| `SCR-PUSH` | Push Notification Settings | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `GET /push/status`<br>`POST /push/subscriptions`<br>`DELETE /push/subscriptions`<br>`POST /push/test` |
| `SCR-AI-CHAT` | AI Assistant / Chat | `/ai` | **PRESENTATION_ONLY** | P0 | `POST /chat`<br>`GET /chat/latest/{conversation_id}` |
| `SCR-AI-CONVERSATIONS` | Conversation History | `MISSING` | **MISSING_UI_BACKEND_READY** | P0 | `GET/POST /chat/conversations`<br>`GET /chat/conversations/{id}/messages`<br>`PATCH/DELETE /chat/conversations/{id}` |
| `SCR-AI-ATTACHMENTS` | Chat Attachments | `embedded` | **MISSING_UI_BACKEND_READY** | P1 | `POST /attachments/analyze` |
| `SCR-AI-VOICE` | Voice Input | `embedded` | **MISSING_UI_BACKEND_READY** | P1 | `POST /audio/transcriptions`<br>`POST /audio/client-events` |
| `SCR-REPORTS` | Reports / KPI Hub | `/reports` | **PRESENTATION_ONLY_NEEDS_SEMANTIC_VALIDATION** | P1 | `/dashboard/stats`<br>`/sql/query`<br>`seller report endpoints` |
| `SCR-PLANNING` | Planning / Scenarios | `MISSING` | **MISSING_UI_BACKEND_READY** | P2 | `GET /planning/metadata`<br>`GET/POST /planning/scenarios`<br>`GET/PUT /planning/scenarios/{id}/values`<br>`POST /planning/scenarios/{id}/transition`<br>`GET /planning/compare` |
| `SCR-WAREHOUSE` | Warehouse Assistant | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `GET /warehouse-assistant/bootstrap`<br>`POST /warehouse-assistant/sync/varanegar`<br>`POST /warehouse-assistant/snapshots/import`<br>`GET /warehouse-assistant/suggestions`<br>`GET/POST /warehouse-assistant/supplier-orders` |
| `SCR-ORG` | Organization Structure | `MISSING` | **MISSING_UI_BACKEND_READY** | P2 | `GET /organization-structure`<br>`GET /organization-structure/proposals`<br>`PATCH /organization-structure/rules/{id}`<br>`POST /organization-structure/proposals/{id}/decision` |
| `SCR-CONTROL` | Control / Personnel | `MISSING` | **MISSING_UI_BACKEND_READY** | P2 | `GET /control/api/bootstrap`<br>`GET /control/api/personnel-directory`<br>`POST /control/api/sync` |
| `SCR-SCHEMA` | Schema Catalog | `MISSING` | **MISSING_UI_BACKEND_READY** | P2 | `GET /chat/schema-catalog`<br>`GET /chat/schema-catalog/object` |
| `SCR-AUTOMATIONS` | Automation Management | `MISSING` | **MISSING_UI_BACKEND_READY** | P2 | `GET/POST /automations`<br>`POST /automations/{id}/pause`<br>`POST /automations/{id}/resume`<br>`DELETE /automations/{id}` |
| `SCR-ACCOUNT` | Account / Change Password | `MISSING` | **MISSING_UI_BACKEND_READY** | P1 | `POST /auth/change-password` |
| `SCR-INSTALL` | PWA / Android Install | `embedded` | **PARTIAL** | P2 | `GET /download/android`<br>`GET /install/android`<br>`service-worker.js` |

## P0 execution order

1. UTF-8/Mojibake repair for `vnext/src` user-visible Persian strings and shell labels.
2. App Shell action wiring: module navigation, notifications, account/profile, and reliable back behavior.
3. Seller flow parity: My Routes → Route Customers → Customer Profile → Visit Workspace.
4. Order flow parity: Previsit start → policy/context → product/catalog → cart/draft → official preview → saved requests → completion.
5. Route Map parity: day route, Neshan map plan/legs, location state, navigation speech.
6. AI parity: conversations → messages → chat submit → attachments → voice.
7. Home live context only after a session-compatible API contract is selected; do not wire privileged API-key dashboard endpoints directly into the seller UI.

## Blocking findings

- User-visible Persian text in multiple `vnext` TS/TSX files is mojibake; this is a P0 quality defect.
- `SellerRoutesScreen` is the only current operational feature screen observed using `useApiQuery`; its drill-down action is disabled.
- Home, AI, Reports, More and most Modules Hub items are presentation shells or non-functional launchers.
- Backend seller/previsit/map functionality is substantially ahead of vNext UI; migration should reuse those APIs rather than recreate business logic client-side.
- Reports/KPI remain `NEEDS_SEMANTIC_VALIDATION` until mapped to an approved Semantic Contract.

## Acceptance contract for each migrated screen

A screen may move to DONE only after: responsive layouts (390/768/1440 minimum), RTL, API wiring, loading/error/empty/offline states, permission handling, keyboard/touch accessibility, visual QA against NeginAI Design Language, feature-parity evidence, and an explicit test result.
