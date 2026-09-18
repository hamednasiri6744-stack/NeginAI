# NGT + GRS + NeginAI Backend Capability Catalog v1

Status: CANONICAL WORKING CATALOG
Date: 2026-09-18
Purpose: preserve every verified capability before information-architecture and UI layout work.

## 1. Governing rule

This catalog is not a screen map. It is the capability inventory behind the product.

Ownership:
- NGT = field-sales operational context and policy.
- GRS = field telemetry, route/activity evidence, region/device state.
- NeginAI Backend = semantic composition, orchestration, workflow state, alerts, AI context, controlled bridges.
- Varanegar remains the commercial/accounting truth where the backend consumes ERP facts.

UI rule:
- one business capability has one canonical owner;
- other screens may show only approved projections;
- source systems are not navigation modules;
- no capability is removed merely because it is not exposed at level 0.

Status legend:
- ACTIVE = live and usable now.
- PARTIAL = live but not fully surfaced/validated.
- GATED = implementation exists but a runtime/semantic gate blocks official use.
- GAP = verified source capability has no bounded NeginAI read model/UI yet.
- DISABLED = intentionally off by safety/configuration.
## 2. NGT catalog

Verified NGT server baseline:
- Server version: 5.9.0.170.
- Verified server binaries: NGT.WebApi / NGT.Business / related DataAccess contracts.
- Verified integration direction: NeginAI Backend -> NGT Web API -> Varanegar BackOffice adapter.
- Direct operational-table writes are not the canonical NGT integration path.

### 2.1 Identity, device and policy
- Seller/personnel identity — NGT.Personnels, NGT.Users — ACTIVE.
- Device-user binding — NGT.DeviceUsers — ACTIVE.
- Device policy/settings — NGT.DeviceSettings, NGT.AppSettings — ACTIVE.
- Shared/base policy values — NGT.BaseValues, NGT.PublicValues — ACTIVE.
- GPS/distance/customer-edit/report/finance visibility policy — ACTIVE/PARTIAL in current UX.

### 2.2 Route, calendar and visit
- Visit templates — NGT.VisitTemplates — ACTIVE.
- Route/path definitions — NGT.VisitTemplatePaths — ACTIVE.
- Route customer membership — NGT.VisitTemplatePathCustomers — ACTIVE.
- Secondary route customers — NGT.VisitTemplatePathSecondaryCustomers — ACTIVE.
- Visit plans and vacations — NGT.VisitPlans / VisitPlanVacations — ACTIVE.
- Explicit day-path overrides — NGT.DayPaths — ACTIVE.
- Tours — NGT.Tours — ACTIVE.
- Calendar templates/holidays — NGT.CalendarTemplates / CalendarTemplateHolidays — ACTIVE.
- Effective route, working/off day and route rotation semantics — ACTIVE.
### 2.3 Customer field-sales context
- Customer master projection — NGT.Customers — ACTIVE.
- Categories — NGT.CustomerCategories — ACTIVE.
- Levels — NGT.CustomerLevels — ACTIVE.
- Main/sub types — NGT.CustomerMainSubTypes — ACTIVE.
- Owner types — NGT.CustomerOwnerTypes — ACTIVE.
- Activities — NGT.CustomerActivities — ACTIVE.
- No-sale reasons — NGT.NoSaleReasons — ACTIVE.
- Customer call/order interaction history — NGT.CustomerCalls / CustomerCallOrders / CustomerCallOrderLines — PARTIAL; underused in current UI.

### 2.4 Catalog, product and image scope
- Product template — NGT.ProductTemplates / ProductTemplateDetails — ACTIVE.
- Seller catalog — NGT.Catalogs / CatalogProducts — ACTIVE.
- Product units — NGT.ProductUnits / Units — ACTIVE.
- Catalog/product images — NGT.ImageInfoes — backend endpoint exists; UI exposure currently GAP/PARTIAL.
- Seller brand scope — backend endpoint exists; current direct UI use is GAP.

### 2.5 Stock, price and commercial policy
- Stock context — NGT.Stocks — ACTIVE.
- Contract/base price context — NGT.ContractPrices — ACTIVE/PARTIAL.
- Allowed order types — NGT.DeviceOrderTypes / OrderTypes — ACTIVE.
- Allowed payment types — NGT.PaymentTypes / PaymentTypeOrders / DealerPaymentTypes — ACTIVE.
- Final official commercial calculation — NGT EVC REST — GATED because current runtime NGT REST configuration is not verified.
- Official discount/prize/credit result — must come from official preview/evidence; never infer final values in UI.
### 2.6 Verified NGT write/sync contracts
- Tour/mobile-data save:
  POST /api/v2/ngt/tour/sync/savedata
  payload root: SyncGetTourViewModel.
- Existing customer profile update:
  CustomerUpdates[] -> NGT transaction + BackOffice adapter.
- Existing customer location update:
  CustomerLocations[] -> NGT route-point/customer update + BackOffice adapter.
- New customer registration:
  CustomerCalls[].IsNewCustomer=true + SyncCustomer -> NGT + BackOffice adapter.
- Presale tour replication:
  GET /api/v2/ngt/tour/PreSale/Replicate/{tourId}.
- Current NeginAI state:
  profile/location edits are local drafts; automatic NGT sync is not active.
- Safety:
  NGT writes must be backend-mediated, idempotent, auditable, permissioned and independently gated.

## 3. GRS catalog

Live grs database snapshot:
- 70 tables.
- Role: field execution evidence and telemetry, not generic HR and not ERP commercial truth.

Verified capability families:
- Personnel — CompanyPersonnels.
- Personnel route assignment — CompanyPersonnelRoutes.
- Customer/product/brand reference context — Customers / Products / Brands.
- Daily activity events — PersonnelDailyActivityEvents.
- GPS/activity points — PersonnelDailyActivityPoints.
- Historical activity/point history — related history tables.
- Regions/territories — RegionAreas / RegionAreaPoints.
- Tracking products/context — TrackingProducts.
- Device/identity/permission state — Devices and related identity/permission tables.
### 3.1 GRS product meaning
GRS can provide evidence for:
- actual field movement,
- route adherence,
- stop/activity timing,
- territory presence,
- device activity/state,
- historical field execution.

Canonical architecture rule:
- NGT owns assigned/effective route and visit policy.
- GRS owns actual field evidence after bounded validation.
- Neshan owns map/navigation service.
- These sources must be fused, not duplicated.

Current NeginAI state:
- GRS is inventoried and validated as a source family.
- Seller Workspace does not yet expose a bounded GRS telemetry read model.
- Visitor UI must therefore treat GRS telemetry as GAP until that read model is implemented and validated.

## 4. NeginAI Backend catalog

Runtime snapshot verified on 2026-09-18:
- OpenAPI paths: 230.
- OpenAPI operations: 253.
- Seller Workspace operations: 32.
- Warehouse Assistant operations: 141.

Operation groups:
- seller-workspace 32
- warehouse-assistant 141
- chat 11
- supplier-portal 9
- automations 8
- planning 8
- schema 8
- auth 5
- definitions 5
- control 4
- organization-structure 4
- push 4
- entities 3
- health 3
- audio 3
- attachments/context/dashboard/history/sql: smaller bounded groups
### 4.1 Seller Workspace
ACTIVE/PARTIAL capabilities:
- authentication/session context,
- assigned routes and route customers,
- customer profile / Customer360 composition,
- visit workspace and visit policy,
- map configuration / map plan / map leg,
- seller brands,
- open invoices and customer-specific open invoices,
- returned cheques,
- distribution in progress,
- voucher/return reporting,
- target pulse with semantic gate,
- previsit context and browse context,
- official preview boundary,
- visit create/read/draft/complete,
- saved requests,
- catalog image delivery,
- previsit warmup.

### 4.2 Semantic/orchestration layer
Backend owns:
- guarded SQL access,
- semantic routes for ERP concepts,
- read-model composition across NGT/ERP/local state,
- entity resolution,
- definitions/schema catalog,
- request orchestration,
- reasoning/context fusion,
- business-time and organization context,
- evidence-aware AI context.

The frontend must not recreate official sales, balance, cheque, inventory, target, settlement or commercial semantics.

### 4.3 Alerts and commercial intelligence seed
Existing backend observers/services can represent:
- route assignment/customer changes,
- returned cheque changes,
- distribution changes,
- voucher returns,
- credit blocks,
- official quote changes,
- price/discount/prize policy changes,
- notification read/ack lifecycle.
### 4.4 AI and assistant
- Chat/conversation backend — ACTIVE.
- Contextual payload/context services — ACTIVE/PARTIAL.
- Ambient AI — PARTIAL.
- Contextual Copilot — capability contract exists; broader in-place UI exposure still incomplete.
- Next Best Action — PARTIAL; must be evidence-backed, not frontend-authored.
- Agent action layer — PARTIAL; actions must call canonical capability APIs.
- Deep AI Workspace — ACTIVE.

### 4.5 Enterprise domains preserved outside Visitor navigation
Warehouse Assistant:
- inventory operations,
- checkbar,
- interwarehouse transfers,
- purchase contracts,
- supplier orders,
- purchase invoices/receipt conversion,
- fulfillment,
- automatic preorders/settings,
- supplier portal,
- sale-price contracts,
- table/SMS/configuration and related support flows.

Admin/Platform:
- planning,
- organization structure,
- control/permissions,
- guarded SQL,
- schema catalog,
- definitions,
- entities,
- automations,
- push,
- audio/attachments,
- health/observability.

These capabilities stay preserved but are role-bounded and must not pollute seller navigation.

### 4.6 Controlled write boundaries
- NGT customer/tour sync: contract verified; direct NeginAI activation still gated.
- Official NGT EVC preview: backend implementation exists; runtime connectivity currently GATED.
- Final Varanegar order bridge: DISABLED.
- Varanegar final commit/numbering: unverified and DISABLED.
- Other controlled warehouse write procedures remain separate, permissioned enterprise workflows.
## 5. Capability fusion map

| Product job | Primary operational source | Supporting source | Backend role | Current state |
|---|---|---|---|---|
| Seller identity/policy | NGT | ERP personnel | compose/authorize | ACTIVE |
| Working day/calendar | NGT | — | read model | ACTIVE |
| Assigned route | NGT | — | read model | ACTIVE |
| Actual route execution | GRS | NGT + Neshan | future telemetry fusion | GAP |
| Visit lifecycle | NGT | NeginAI local state | workflow | ACTIVE |
| Customer360 | NGT + ERP | GRS later | compose semantics | ACTIVE/PARTIAL |
| Catalog/product/unit | NGT | ERP stock/price evidence | selling context | ACTIVE |
| Product image | NGT | — | media delivery | GAP/PARTIAL |
| Stock/base price | NGT + ERP | — | validate/compose | ACTIVE/PARTIAL |
| Official quote/discount/prize | NGT EVC | ERP rule evidence | normalize/validate | GATED |
| Saved request | NeginAI local state | NGT preview | durable workflow | ACTIVE |
| Final ERP order | controlled bridge | NGT/ERP | transactional bridge | DISABLED |
| Field telemetry | GRS | Cloud sibling source | bounded read model | GAP |
| Alerts | multi-source | local state | event lifecycle | ACTIVE |
| AI guidance | approved read models | all verified sources | explain/prioritize/act | PARTIAL |

## 6. Immediate architecture implications

1. Preserve every capability above even if it is not a bottom-nav item.
2. Route UI must combine NGT planned route with future GRS actual execution without duplicating route ownership.
3. Orders must use NGT catalog/policy and official EVC only when available; no invented commercial math.
4. Customer360 should consume NGT call/order history and customer-specific finance depth instead of duplicating separate workflows.
5. Backend enterprise domains remain available behind role-bounded workspaces.
6. GRS telemetry read model is a P0 architecture gap before claiming live route execution.
7. NGT REST/EVC runtime state and final ERP write state must remain visibly distinct.
8. This catalog is the capability source for subsequent screen placement; UI elements are mapped after ownership, not before.

Machine-readable companion:
docs/catalog/NGT_GRS_BACKEND_CAPABILITY_CATALOG_V1.csv
