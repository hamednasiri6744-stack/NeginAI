# NeginAI Product Architecture v1 — Inventory-Driven Draft

> Derived from NEGINAI_SYSTEM_INVENTORY_2026-09-18.md.
> This is a product/domain architecture, not a visual redesign.

## 1. Architecture rule

Every user-visible concept must have:
1. one owning product domain,
2. one authoritative source or semantic contract,
3. one backend capability boundary,
4. one primary interaction location,
5. optional cross-module signals only through shared intelligence/alerts.

No module may duplicate another module merely because the data is available.

## 2. Source-of-truth layers

### Operational field context — NGT
Owns:
- seller/device permissions
- today's effective route
- route membership
- visit policy
- customer membership
- seller product template/catalog scope
- allowed order/payment types
- operational stock/price context required for previsit

### ERP commercial truth — Varanegar
Owns:
- finalized sales and returns
- order conversion
- invoice/open balance
- receipts/settlement/cardex
- cheque/returned cheque
- inventory/cardex
- distribution
- commercial rule sources
- purchase-cost/profitability basis

Schemas: SLE, GNR, Acc, inv, FRU, ICA, dbo.

### Field telemetry — Cloud / grs
Owns/potentially owns:
- actual personnel activity
- GPS point/event history
- device state
- route/region activity
- field execution telemetry

This is not yet a Seller Workspace source and requires a dedicated read model before product use.

### Navigation — Neshan
Owns:
- map presentation/service
- route navigation/leg support

### NeginAI application state
Owns:
- visit drafts
- saved order requests
- alert state/read/ack
- planning scenarios
- automations
- chat/conversation state
- semantic metadata/definitions

### Controlled write bridges
Own:
- final ERP mutations only after explicit validation and feature flags.
- never mixed with read-only source access.

## 3. Cross-cutting platform layers

### A. Semantic Contract Layer
Purpose:
- define exact meaning of sales, balance, target, settlement, receipt, route, etc.
- prevent each screen from reinterpreting ERP data.

Existing seed:
- varanegar_knowledge.py
- reporting_policy.py
- business_terms.py
- target semantic status

### B. Seller Workspace Read Model
Purpose:
- compose NGT + ERP facts for seller-facing use.
- exposes route/customer/financial/distribution/map/previsit context.

Existing API:
- /seller-workspace/*

### C. Commercial Intelligence Layer
New logical layer; must use evidence, not invented scores.

Inputs:
- validated performance/target state
- route and visit state
- customer sales/history
- open invoices and returned cheques
- catalog and stock
- current price/commercial-policy changes
- distribution/return state
- alerts
- eventually Cloud/grs field telemetry

Outputs:
- Next Best Action
- verified opportunity evidence
- urgency/risk evidence
- commercial change summary
- action path
- source/evidence metadata
- semantic status/confidence where needed

Rule:
No arbitrary "AI score" unless a separate validated scoring model is built.

### D. Alert/Event Layer
Existing seed:
- operational_notification_service.py

Categories:
- price
- promotion/reward
- finance/credit
- route/customer
- distribution
- return
- official quote

Alert Center is global; it is not owned by one bottom-nav module.

## 4. Primary seller product architecture

### 4.1 Home — Commercial Command
Job:
**What matters now, and what should I do next?**

Owns:
- current commercial state
- Next Best Action
- momentum
- most important risk
- most important opportunity
- top operational signal
- alert entry point

Does NOT own:
- route details
- customer list
- report dashboards
- full catalog
- detailed finance lists

Depth:
- L0 Command state / Next Best Action
- L1 Performance / Opportunity / Risk / Operations
- L2 supporting evidence
- action may transition to owning module

Source:
Commercial Intelligence Layer + validated Seller Workspace facts.

### 4.2 Customers — Customer Intelligence
Job:
**Who should I understand, sell to, follow up, or protect?**

Owns:
- customer segmentation/navigation
- Customer360
- sales relationship
- financial relationship
- visit/order history
- customer-specific open invoice/cardex/cheque context
- customer-specific opportunity evidence

Depth:
- L0 customer segments/priorities
- L1 customer list in selected segment
- L2 Customer360
- L3 sales / finance / visit / history detail

Must consume:
- customer-specific open-invoices endpoint
- NGT profile/visit workspace
- ERP finance/sales facts

### 4.3 Route — Field Execution
Job:
**Where do I go next, what is the state of today's field work, and what do I do at this stop?**

Owns:
- today's route
- map
- stop sequence
- route status
- location policy
- route-local customer list
- stop/visit execution
- visit outcome

Does NOT route to Customers merely to show route customers.

Depth:
- L0 map + next operational action
- L1 route/stop plan
- L2 selected stop/visit workspace
- L3 visit outcome / order handoff

Future source:
NGT plan + Neshan navigation + Cloud/grs actual activity telemetry.

### 4.4 Orders — Selling Workspace
Job:
**What can I sell to this customer, under what official commercial conditions, and how do I complete the request safely?**

Owns:
- selected customer selling context
- product discovery
- seller catalog
- brand/group filters
- product detail
- quantities
- stock
- order/payment type
- official preview
- discount/prize
- credit restriction
- draft/saved request
- final submission state

Depth:
- L0 customer + commercial context + sellable discovery
- L1 brand/group/catalog
- L2 product/order line editing
- L3 official NGT preview and restrictions
- L4 saved request or verified final commit

Important runtime truth:
NGT REST preview is currently not configured.
Final Varanegar bridge is currently disabled.
UI must reflect these states honestly.

### 4.5 Reports — Analysis
Job:
**Why did something happen, what changed, and where should I investigate?**

Owns:
- analytical questions
- comparisons
- detailed financial/commercial analysis
- historical patterns
- drill-down tables

Depth:
- L0 analytical domains/questions
- L1 analytical summary
- L2 detailed records
- L3 specific entity/document when needed

Scroll is allowed in analytical detail.

Reports must not duplicate Home operational signals or Route execution state.

## 5. Global surfaces

### Alert Center
Entry: global bell / contextual urgent cues.

Owns:
- cross-domain change/urgency
- price changes
- discount/reward changes
- finance/credit alerts
- route changes
- distribution/return alerts
- read/ack lifecycle

### Negin AI
Not a separate data silo.

Role:
- contextual reasoning over the current module/entity.
- should inherit module context.
- must cite or expose the business evidence it used when giving operational guidance.

Examples:
- Home: explain Next Best Action.
- Customer360: analyze this customer.
- Route: explain route/visit priority.
- Order: explain product/commercial context.
- Reports: analyze current report domain.

### Profile / Settings
Owns:
- identity
- permissions/account
- real preferences only
- session/logout

No fake toggles.

## 6. Role-bounded workspaces outside seller navigation

### Admin / Planning
Separate role workspace.
Owns:
- planning scenarios
- targets
- organization structure
- schema/definitions where authorized
- control operations

### Warehouse Operations
Separate enterprise workspace/product surface.
Owns:
- inventory operations
- automatic preorders
- supplier orders
- purchase contracts
- purchase invoices
- checkbar
- interwarehouse transfer
- receipt/fulfillment
- supplier portal

Do not mix warehouse modules into Visitor bottom navigation.

## 7. Bottom navigation recommendation

For seller role:
1. Home — Commercial Command
2. Route — Field Execution
3. Order — Selling Workspace (primary central action)
4. Customers — Customer Intelligence
5. Reports — Analysis

Global, outside bottom-nav ownership:
- Alerts
- Negin AI
- Profile

This keeps each stable user job represented exactly once.

## 8. Data ownership matrix

| Concept | Owner module | Source truth |
|---|---|---|
| Current route | Route | NGT |
| Route customers | Route context / Customer entity | NGT |
| Full customer intelligence | Customers | NGT + GNR + ERP finance/sales |
| Customer open invoices | Customers | Acc |
| Returned cheque | Customers/Reports; global alert | Acc |
| Stock available to sell | Orders | NGT + inventory context |
| Base/contract price | Orders | NGT/SLE |
| Official final quote | Orders | NGT EVC |
| Discount/prize result | Orders | NGT EVC, with ERP rule evidence |
| Sales performance | Home/Reports | SLE/dbo semantic contract |
| Target achievement | Home/Reports | planning + validated sales KPI |
| Distribution execution | Route signal / Reports detail | SLE/dbo |
| Price/promo change | Global Alert + Home signal | operational event layer |
| Actual GPS/activity history | Route | Cloud/grs after read-model validation |
| Saved order request | Orders | NeginAI local application state |
| Final ERP order | Orders | controlled Varanegar bridge |

## 9. Immediate backend gaps before major UI rebuild

### P0
1. Configure and verify NGT REST/EVC in a controlled environment.
2. Keep final Varanegar commit disabled until numbering/transaction contract is verified.
3. Define Commercial Intelligence read model.
4. Validate target/sales semantic contract before official target motivation.

### P1
5. Expose Cloud/grs field telemetry through a bounded read-only Seller Workspace API.
6. Use customer-specific open-invoices endpoint in Customer360.
7. Wire seller /brands endpoint to Selling/Commercial Intelligence.
8. Use catalog image endpoint in Orders.
9. Use previsit warmup to improve perceived latency.

### P2
10. Expand customer cardex/settlement/receipt drill-down.
11. Add verified historical opportunity features only after evidence rules are defined.
12. Consider push delivery for high-severity operational alerts.

## 10. UI architecture rules

- Bottom-nav modules are domains, not shortcuts.
- In-module detail uses depth; do not jump to another bottom-nav module for a detail owned by the current domain.
- Cross-module transition occurs only when the user's job genuinely changes.
- Level 0 should be decision/action-oriented.
- Long scroll is allowed only for inherently sequential/detail content.
- Glass/Neu/Living design is presentation behavior, not information architecture.
- Motion never substitutes for domain depth.
- Home never duplicates entire modules.
- Every action should be backed by a real capability or clearly presented as unavailable.

## 11. Build sequence

1. Freeze visual experimentation.
2. Stabilize source/capability contracts.
3. Build Commercial Intelligence API/read model.
4. Rebuild Home on that read model.
5. Normalize Route around execution.
6. Complete Customer360 data depth.
7. Complete Orders official commercial flow.
8. Reframe Reports around analysis.
9. Integrate Cloud/grs telemetry after validation.
10. Then do final Living UI / Design System polish across stable architecture.
