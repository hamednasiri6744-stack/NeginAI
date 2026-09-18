# NeginAI Architecture Contract v1

Status: CANONICAL / APPROVED PRINCIPLES  
Date: 2026-09-18  
Basis: `docs/NEGINAI_SYSTEM_INVENTORY_2026-09-18.md` + current backend/source inventory.

This contract governs product architecture before any further screen implementation.

## 1. Non-negotiable principles

### 1.1 Inventory-first
No user-facing capability may be invented from UI preference alone.
Every capability must map to an accepted source, semantic contract, backend boundary, or explicitly tracked future gap.

### 1.2 Preserve existing source systems
NeginAI does not replace or reinterpret the current operational sources casually.

Source roles:
- **Varanegar ERP** — commercial/accounting truth: sales, returns, finance, inventory, distribution, commercial rules, purchase-cost basis.
- **NGT** — field-sales operational context: seller/device policy, route/calendar, visit policy, customer membership, catalog scope, order/payment policy.
- **Cloud / grs** — field telemetry and activity: personnel movement, GPS/activity history, regions, device state.
- **Neshan** — map/navigation services.
- **NeginAI Backend** — semantic/orchestration/read-model layer, local workflow state, alerts, AI context, controlled write bridges.

### 1.3 One capability, one canonical owner
Every business capability has exactly one `owner_domain`.
A capability may appear elsewhere only as an approved projection.

### 1.4 Projection is not duplication
Allowed cross-module projections are intentionally shallow:
- `signal` — one actionable indicator.
- `badge` — state/count only.
- `summary` — compact read-only summary.
- `context` — information needed to complete the current job.
- `aggregate` — analytical rollup.
- `deep-link` — transition to the canonical capability.
- `alert` — event/change representation.

A projection must not recreate the full workflow, filters, actions, and detail of the canonical capability.

### 1.5 Reusable UI is allowed; duplicated business behavior is not
The same shared Design System component may appear on many screens.
The same business operation must not be independently implemented in several screens.

Example:
- A `StatusChip` can be reused everywhere.
- Returned-cheque management cannot be implemented independently in Home, Customer360, Reports, and Alerts.

### 1.6 Navigation represents jobs, not databases
Varanegar, NGT, GRS, Cloud, Neshan, SQL schemas, and API families are source layers, not navigation items.

Stable seller jobs:
1. **Today / Mission Control**
2. **Route / Field Execution**
3. **Order / Selling Workspace**
4. **Customers / Customer Intelligence**
5. **Reports / Analysis**

Global surfaces:
- Alert Center
- Negin AI / contextual copilot
- Profile / Settings

Contextual depth workspaces:
- Finance / Collections detail
- Distribution / Returns detail
- Visit workspace
- Product detail
- Official preview / order validation

### 1.7 Domain ownership is separate from screen placement
A capability can be owned by Finance & Collections while being opened inside Customer360 as contextual depth.
The screen location does not change its business owner.

### 1.8 Depth before sprawl
Do not expose every backend capability at level 0.
Use:
`Overview -> Context -> Detail -> Action`

Mobile level 0 must prioritize decision and action.
Long scroll is reserved for inherently sequential/detail-heavy content.

### 1.9 Source truth -> semantics -> workflow -> presentation
Required layering:
`Source -> Semantic Contract -> Backend Read Model / Workflow -> Intelligence -> UI Projection`

UI code must not define accounting/commercial meaning.

### 1.10 AI is cross-cutting, not a competing data silo
AI may:
- summarize,
- explain,
- detect evidence-backed risk/opportunity,
- recommend next action,
- invoke approved agent actions.

AI may not:
- invent source facts,
- create an independent definition of ERP KPIs,
- duplicate domain workflows,
- hide the evidence used for operational guidance.

Domain owns truth. AI explains, predicts, prioritizes, and acts under policy.

## 2. Source ownership boundaries

### NGT
Canonical for:
- seller identity/device/order policy context,
- working calendar,
- assigned/effective routes,
- route customer membership,
- visit policy,
- customer field-sales classifications,
- seller catalog/product template,
- product units,
- allowed order/payment methods,
- operational context needed for previsit.

### Varanegar / ERP
Canonical for verified commercial/accounting facts:
- finalized sales/returns,
- customer balances,
- open invoices,
- receipts/settlement,
- cheque/returned cheque,
- cardex,
- inventory/cardex,
- distribution,
- ERP commercial-rule evidence,
- confirmed purchase-price/profitability basis.

### Cloud / grs
Reserved for validated field telemetry:
- actual activity events,
- GPS/activity points and histories,
- device state,
- region/route activity.

Until a bounded Seller Workspace read model exists, these are inventory capabilities, not active Visitor UI facts.

### Neshan
Canonical navigation provider for map rendering/routing services only.
NGT remains authoritative for assigned route/customer membership.

### NeginAI application/backend
Owns:
- orchestration,
- semantic composition,
- visit drafts,
- saved requests,
- notification read/ack state,
- offline snapshot state,
- chat/AI context,
- controlled integration/write bridges.

## 3. Write boundary contract

Read access and ERP mutation must remain separate.

Controlled write bridges:
- remain feature-flagged,
- remain transactional,
- remain auditable,
- remain disabled until explicitly verified.

Current inventory truth:
- official NGT EVC REST preview is not operational until NGT API configuration is verified.
- final Varanegar order commit is disabled/unverified.
- UI must distinguish draft, saved request, official preview, and final ERP commit.

No UI wording may imply an unavailable write has completed.

## 4. Semantic integrity contract

The backend semantic layer is authoritative for terms such as:
- sales,
- returns,
- balance,
- invoice,
- receipt,
- settlement,
- cheque,
- returned cheque,
- inventory,
- distribution,
- target/KPI where validated.

The frontend must not create alternate calculations for official KPIs.
Unvalidated KPI semantics remain gated.

## 5. Capability registration gate

Before implementing or moving a business feature, the registry must contain:
- `capability_id`
- `capability_name`
- `scope`
- `owner_domain`
- `canonical_surface`
- `primary_source`
- `semantic_authority`
- `backend_boundary`
- `allowed_projections`
- `interaction_mode`
- `availability`
- `notes`

No registry entry -> no new user-facing implementation.

## 6. Duplicate prevention rules

A pull request violates architecture if it:
1. gives one capability multiple canonical owners,
2. implements a second full workflow for a capability,
3. moves ERP semantics into frontend code,
4. exposes a source system as a user navigation module,
5. promotes an unverified/disabled capability as active,
6. creates an AI-only duplicate of an existing domain function,
7. adds a new card/element without a registered capability or presentation-only justification.

## 7. Seller information architecture

### Today / Mission Control
Purpose: what matters now and what should I do next?

Allowed:
- projections from Route, Finance, Commercial, Distribution, Alerts, AI.
- Next Best Action with evidence/deep-link.

Not allowed:
- full finance lists,
- full route management,
- full catalog,
- report dashboards.

### Route / Field Execution
Own interaction location for:
- route execution,
- map,
- stop sequence,
- visit execution,
- location/telemetry context.

### Order / Selling Workspace
Own interaction location for:
- catalog/product discovery,
- quantity,
- stock/price context,
- order/payment policy,
- preview,
- discount/prize/credit result,
- draft/saved request/final submission state.

### Customers / Customer Intelligence
Own interaction location for:
- customer discovery/segmentation,
- Customer360,
- customer-specific relationship context.

Finance, distribution, sales-history, and visit-history appear as contextual depths while retaining their domain ownership.

### Reports / Analysis
Own interaction location for:
- analytical questions,
- comparisons,
- trends,
- aggregates,
- historical drilldown.

Reports consume canonical facts; they do not redefine operational workflows.

## 8. Enterprise domains outside Visitor navigation

The backend contains capabilities that must be preserved without polluting seller navigation.

### Warehouse Operations
Separate role-bounded workspace:
- checkbars,
- interwarehouse transfers,
- purchase contracts,
- supplier portal,
- automatic preorders,
- supplier orders,
- inventory operations,
- fulfillment,
- purchase invoices,
- supply scope and related settings.

### Admin / Planning
Separate role-bounded workspace:
- planning scenarios,
- organization structure,
- control console,
- permissioned definitions/schema administration.

### Platform / Knowledge
Infrastructure capabilities:
- guarded SQL,
- schema catalog,
- definitions,
- entity resolution,
- automation,
- chat,
- attachments/audio,
- push,
- OAuth/session/auth.

These remain available to their intended consumers but are not seller modules unless a registered job requires them.

## 9. AI contract

AI has five product modes:
1. Ambient AI
2. Contextual Copilot
3. Next Best Action
4. Agent Action Layer
5. AI Workspace

Rules:
- AI receives current module/entity context through Context Fusion.
- AI output must retain evidence/source traceability for operational guidance.
- AI actions must call the canonical capability owner, never a parallel duplicate workflow.
- High-impact mutations require the capability's existing authorization/confirmation policy.
- AI Workspace is a deep reasoning surface, not the owner of ERP capabilities.

## 10. UX contract

Modern/mobile-first behavior is achieved by architecture, not by hiding features.

Rules:
- preserve full capability depth,
- progressive disclosure,
- contextual drilldown,
- minimal level-0 density,
- shared components,
- one canonical action location,
- no dashboard-card proliferation,
- no unnecessary page switching,
- RTL/mobile-first,
- >=44px touch targets,
- reduced-motion support,
- state/data-driven motion only.

## 11. Governance

Canonical registry:
`docs/architecture/NEGINAI_CANONICAL_CAPABILITY_REGISTRY_V1.csv`

Validation:
`scripts/architecture/validate_capability_registry.py`

This contract supersedes page-first feature placement decisions.
Visual design may evolve; capability ownership and source semantics must remain stable unless this contract and registry are deliberately versioned.
