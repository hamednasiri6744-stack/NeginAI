# NeginAI Target Information Architecture v1

Status: CANONICAL TARGET STRUCTURE  
Date: 2026-09-18  
Scope: Visitor vNext information architecture only  
Visual design: already fixed separately; this document does not redesign appearance.

This structure is derived from the accepted system inventory, capability registry, and current UI audit.

## 1. Global product shell

Persistent seller navigation:
1. Today
2. Route
3. Order
4. Customers
5. Reports

Global surfaces outside bottom-navigation ownership:
- Alert Center
- Contextual Negin AI
- Profile / Settings
- Sync / Offline status

Rules:
- source systems are never navigation items,
- a business workflow has one canonical interaction location,
- cross-module appearances are shallow projections,
- shared visual components are reused globally,
- domain logic is never duplicated in multiple screens.

## 2. Today / Mission Control

Job:
What matters now and what should I do next?

### L0 — Command surface
Own content:
- seller identity context
- current working-day state
- current time/date
- effective route progress summary
- one evidence-backed Next Best Action
- up to four live signals

Allowed live signals:
- operational alert severity
- finance risk
- distribution exception
- validated performance/target signal

Not allowed:
- customer lists
- finance lists
- cheque details
- report tables
- route stop manager
- product catalog
- independent AI scoring

### L1 — Signal explanation
A signal may open a compact contextual explanation with:
- what changed
- evidence/source
- why it matters
- canonical destination

No full workflow is implemented here.

### L2 — Canonical transition
Examples:
- Route signal -> Route
- returned cheque -> Customer finance / finance context
- sales analysis -> Reports
- alert -> Alert Center
- order opportunity -> Orders

## 3. Customers / Customer Intelligence

Job:
Who should I understand or follow up?

### L0 — Customer navigation
- search
- route-aware context
- customer segments
- pending / completed status
- financial-attention filter as projection only

### L1 — Customer list
Each row owns only:
- identity
- address/contact
- route/visit state
- compact financial attention badge
- call
- navigate
- open Customer360

No full finance or visit workflow in the list.

### L2 — Customer360
Canonical customer context:
- identity and classification
- permitted editable draft fields
- contact/location
- relationship summary
- contextual actions

Contextual actions:
- start/continue visit -> Route / Visit Workspace
- start order -> Orders
- call
- navigation
- contextual AI

### L3 — Customer360 depths

#### Overview
- customer master
- classification
- location
- permitted profile draft edits

#### Finance
Owned by Finance & Collections but rendered in customer context:
- balance
- customer-specific open invoices
- cardex
- receipts/collections
- settlement
- cheque history
- returned cheque state

#### History
Owned customer relationship history:
- visit history
- order history
- NGT call history
- saved request/final order references

Rule:
Customer360 composes context but never redefines finance semantics.

## 4. Route / Field Execution

Job:
Where do I go next and what do I do at this stop?

### L0 — Map execution surface
- effective NGT route
- Neshan map/navigation
- current position
- selected/next stop
- route progress
- source-backed route ordering mode
- compact stop context

### L1 — Stop plan
Expandable route-local list only:
- stop order
- customer identity
- ETA/distance
- location state
- visit state
- allowed finance warning projection

This is not the global customer directory.

### L2 — Visit Workspace
- start visit
- active visit timer/state
- NGT policy
- no-order/no-visit reason
- visit outcome
- order handoff
- customer-profile handoff
- contextual AI

### L3 — Field intelligence
When validated:
- Cloud/grs actual movement
- stop duration
- actual-vs-plan
- location events
- route execution telemetry

Rule:
GRS/Cloud enrich Route. They do not become a separate user module.

## 5. Orders / Selling Workspace

Job:
What can I sell and under what valid commercial conditions?

### L0 — Selling context
- selected customer
- visit/session state
- assigned route context
- browse/working-day state
- saved requests entry

### L1 — Discovery
- product search
- seller catalog
- brand scope
- groups
- product image
- orderable/low/out-of-stock filters

### L2 — Product interaction
- product identity
- units
- stock
- indicative/base contract price
- quantity editing
- add/update cart

### L3 — Cart and policy
- cart lines
- unit/quantity
- order type
- payment type
- warehouse when policy allows
- indicative subtotal

### L4 — Official commercial preview
Only when NGT EVC is operational:
- official gross
- discount
- tax/charge
- net
- gift/prize output
- credit result
- restrictions

If unavailable:
show explicit unavailable/gated state.
Do not simulate official output.

### L5 — Save / submit state
Clearly separate:
1. draft
2. saved request
3. official preview
4. final Varanegar commit

Final ERP commit remains unavailable until its bridge contract is verified.

## 6. Reports / Analysis

Job:
Why did this happen and where should I investigate?

### L0 — Analysis domains
- Sales
- Finance
- Returns
- Distribution
- Inventory
- Profitability
- Target only when semantically validated

### L1 — Summary
- trend
- comparison
- aggregate
- exception distribution
- period context

### L2 — Analytical drilldown
- customer-level records
- document-level records
- ranked lists
- historical detail

### L3 — Canonical entity/document
Deep link to:
- Customer360
- finance context
- distribution context
- order/request
- other owning domain

Reports never owns operational actions.

## 7. Alert Center

Global surface. Not a bottom-nav module.

Owns:
- alert/event list
- exact source provenance
- severity
- category
- read
- acknowledge
- action path
- live update

Categories may include:
- finance/credit
- route/customer
- price
- promotion/reward
- official quote
- distribution
- return

Alert Center owns event lifecycle only.
It does not own the underlying business workflow.

## 8. Negin AI

AI is cross-cutting.

### Ambient AI
Appears as evidence-backed signals in current context.

### Contextual Copilot
Primary interaction:
an in-place sheet attached to current module/entity.

Examples:
- Customer360 -> analyze this customer
- Route -> explain this stop/priority
- Orders -> explain commercial context
- Reports -> analyze this report
- Today -> explain Next Best Action

### Next Best Action
Rendered primarily on Today.
Produced by backend intelligence.
Must include evidence and canonical action path.

### Agent Actions
Run through canonical capability APIs.
Never recreate a second workflow.

### AI Workspace
Deep reasoning space for broader conversation and multi-domain analysis.
It is not the owner of ERP capabilities.

## 9. Element uniqueness matrix

| Element | Canonical location | Other appearances |
|---|---|---|
| Working calendar | Today | Route/Orders context only |
| Full route execution | Route | Today summary only |
| Customer directory | Customers | Route stop list is route-local only |
| Customer identity | Customer360 | Orders/Route summary only |
| Customer finance detail | Customer360 > Finance | Today signal; Reports aggregate; Orders restriction context |
| Returned cheque detail | Finance context | Today alert; Customer badge; Reports aggregate; Alerts event |
| Catalog | Orders | Customer/Today only opportunity signal |
| Product details | Orders | none as full duplicate |
| Stock for selling | Orders | Reports aggregate only |
| Official price/discount/prize | Orders Preview | Alerts/Reports projection only |
| Visit workflow | Route | Customer/Orders deep-link or context only |
| Distribution detail | Distribution contextual depth | Today signal; Customer summary; Reports aggregate |
| Sales analysis | Reports | Today compact performance signal |
| Target achievement | Today + Reports analysis | only after semantic validation |
| Alerts | Alert Center | global badge/signal only |
| Contextual AI | current module sheet | deep AI Workspace optional |
| Profile/session | Profile / Settings | AppHeader identity projection only |

## 10. Shared UI primitive uniqueness

Canonical shared components:
- AppHeader
- BottomDock
- BottomSheet
- SegmentedControl
- FeedbackState
- Surface
- StatusChip
- Metric / Progress
- QuantityStepper
- InsightCard
- EntityHeader
- VisitorPicker where applicable

Rules:
- screens compose these primitives,
- screens do not fork visual copies of the same primitive,
- domain-specific content can differ,
- business behavior stays with capability owner.

## 11. Migration sequence

1. unify shared shell primitives with no business behavior change
2. simplify Today to command + NBA + signals
3. complete Customer360 canonical depths
4. normalize Route around field execution and validated telemetry
5. complete Orders source wiring and gated official preview
6. reframe Reports as analysis
7. move AI interactions into contextual sheets
8. preserve deep AI Workspace
9. keep Warehouse/Admin/Platform outside Visitor navigation

## 12. Acceptance rule

A future screen is acceptable only when:
- every business element maps to one capability ID,
- each element is in its canonical surface or approved projection,
- no full workflow is duplicated,
- unavailable capabilities are visibly gated,
- source and semantic authority are preserved,
- shared UI primitives are not reimplemented locally.
