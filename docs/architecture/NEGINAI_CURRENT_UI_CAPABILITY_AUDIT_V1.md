# NeginAI Current UI Capability Audit v1

Status: CANONICAL AUDIT  
Date: 2026-09-18  
Scope: Visitor vNext only  
Important: this audit does **not** approve the current visual design. The current UI remains rejected as a final product direction.

Source basis:
- `docs/NEGINAI_SYSTEM_INVENTORY_2026-09-18.md`
- `docs/NEGINAI_PRODUCT_ARCHITECTURE_V1.md`
- `docs/architecture/NEGINAI_ARCHITECTURE_CONTRACT_V1.md`
- `docs/architecture/NEGINAI_CANONICAL_CAPABILITY_REGISTRY_V1.csv`
- actual current Visitor screen source files in `vnext/src/components`

Machine-readable audit:
- `docs/architecture/NEGINAI_CURRENT_UI_CAPABILITY_AUDIT_V1.csv`

Validator:
- `scripts/architecture/validate_ui_capability_audit.py`

## 1. Audit result

79 current or required UI elements were mapped to canonical capabilities.

Decision counts:
- KEEP: 32
- PROJECTION_ONLY: 13
- MOVE: 9
- DUPLICATE: 4
- MERGE: 2
- MISSING: 19

Priority:
- P0: 15
- P1: 59
- P2: 5

Interpretation:
- Most existing data/workflow capability can be preserved.
- The main problem is not lack of backend capability.
- The main problem is **placement, ownership, duplicate presentation, missing contextual depth, and a few semantic/runtime gates**.
- No broad feature deletion is justified by this audit.

## 2. Highest-risk architecture findings

### P0 — Home Next Best Action is currently frontend-authored
Current Home chooses an action using a local precedence chain:
alerts -> returned cheque -> next route stop -> AI fallback.

This violates the intended Commercial Intelligence contract because prioritization belongs to a backend/evidence-backed intelligence read model.

Decision:
**MOVE**

Target:
`CAP-AI-003 Next Best Action`

Required:
- backend Commercial Intelligence read model,
- evidence metadata,
- canonical action path,
- no arbitrary frontend score or priority.

### P0 — Target is still semantically gated
Target display exists but official target/sales semantic validation is not complete.

Decision:
**KEEP on Today surface but GATED**

No official target motivation or achievement claim until the semantic contract is validated.

### P0 — Customer360 finance depth is incomplete
Customer360 currently shows a finance summary but does not consume the existing customer-specific open-invoice endpoint directly and lacks canonical drilldown for:
- open invoice detail,
- cardex,
- receipts/collections,
- settlement,
- cheque history.

Decision:
**MISSING**

These capabilities belong to Finance & Collections while being presented contextually inside Customer360.

### P0 — Route telemetry from Cloud / grs is absent
Current Route uses NGT + Neshan but does not yet expose the actual field-activity telemetry inventoried in Cloud/grs.

Decision:
**MISSING**

Do not query those stores directly from the frontend.
First create a bounded read-only Seller Workspace telemetry model.

### P0 — Route visit score requires semantic evidence
The Route screen displays a visit score from backend/workspace analytics when present.

Decision:
**PROJECTION_ONLY / GATED**

The score must be hidden or explicitly qualified until its definition and evidence are registered.

### P0 — Official NGT Preview is a runtime gate
Orders already contains UI for:
- official preview,
- official discount,
- gift/prize results,
- credit control,
- restrictions.

The inventory says NGT REST/EVC is not configured in the current runtime.

Decision:
**KEEP capability; gate availability**

The UI must never imply official availability before the EVC connection is verified.

### P0 — Saved Request and final Varanegar order must remain distinct
Current Orders can store a local/saved request.
Final Varanegar commit remains disabled and numbering is unverified.

Decision:
- Saved Request: **KEEP**
- Final Varanegar commit: **MISSING / DISABLED**

Product language must not blur these two states.

### P0 — Alert provenance is currently collapsed
Notifications currently converts both `NGT` and `varanegar` sources into one combined label.

Decision:
**MERGE must be reversed**

Operational evidence must preserve exact source provenance.

### P0 — Contextual AI is missing
The deep AI Workspace exists.
Customer360 Route and Reports currently navigate away to it.

Decision:
- Deep AI Workspace: **KEEP**
- Contextual Copilot: **MISSING**
- current page-jump buttons: **MOVE**

Target pattern:
current module/entity -> contextual AI sheet -> optional deep AI Workspace.

## 3. Screen ownership decisions

### Home / Today
Canonical job:
**What matters now and what should I do next?**

Keep:
- working-day/date state,
- compact route progress,
- one alert signal,
- one financial-risk signal,
- one distribution signal,
- target only when semantically valid,
- one evidence-backed Next Best Action.

Remove as independent Home workspaces:
- second performance deck,
- second risk deck,
- second Today deck,
- second intelligence deck,
- detailed open-invoice analysis,
- detailed returned-cheque analysis,
- detailed returns analysis.

Those are either duplicate Home projections or belong to canonical domain depth.

Target Home hierarchy:
`Command state -> Next Best Action -> 3-4 signals -> deep link`

Not:
`dashboard -> portal -> second portal -> duplicate detail`.

### Customers
Canonical job:
**Find and understand the customer.**

Keep:
- customer discovery,
- search,
- pending/completed/all segmentation,
- Customer360 entry,
- call/navigation utility actions.

Financial attention:
projection only.
It may filter or badge customers but may not own cheque/collection workflow.

Route selector:
context only for browse mode.
It must not become a second Route manager.

### Customer360
Canonical job:
**Understand and act on this customer without losing context.**

Keep:
- identity,
- customer edit draft under current permission semantics,
- address/location context,
- call/navigation actions,
- customer relationship summary,
- contextual finance section,
- visit/order transitions.

Move:
- AI from a standalone card/page-jump into contextual copilot.

Add:
- customer-specific open invoices,
- cardex,
- collections,
- settlement,
- cheque history,
- real NGT call/order timeline.

Customer360 may host these as contextual depth but does not redefine finance or visit semantics.

### Route / Field Execution
Canonical job:
**Where next and what happens at this stop?**

Keep:
- effective route,
- map,
- stop ordering,
- selected stop,
- start/continue visit,
- timer,
- outcome,
- NGT outcome reasons,
- order/customer handoff.

Finance:
debt/risk is projection only.

AI:
contextual sheet rather than page replacement.

Add:
Cloud/grs telemetry only after bounded read model validation.

### Orders / Selling Workspace
This is currently the closest screen to its canonical domain.

Keep:
- customer selling context,
- product discovery,
- catalog,
- units,
- stock,
- indicative/base price,
- cart,
- quantity,
- order/payment/warehouse policy,
- official preview output when available,
- discount/prize/credit output when officially returned,
- saved request.

Required corrections:
- reconcile brand filter with seller brand scope endpoint,
- use real product/catalog image endpoint correctly,
- use previsit warmup,
- visually gate EVC when unavailable,
- rename saved-request language so it cannot be mistaken for final ERP order,
- keep final Varanegar order unavailable until verified.

### Reports / Analysis
Canonical job:
**Why did this happen and where should I investigate?**

Current finance/distribution/returns analytical drilldowns are valid if they remain read-only analytics.

Missing:
- validated sales analysis,
- target analysis after semantic validation,
- inventory analysis,
- profitability using verified last-purchase-price semantics.

AI analysis:
in-place contextual copilot first; deep AI Workspace optional.

### Alert Center
Keep:
- global list,
- filters,
- read lifecycle,
- acknowledge lifecycle,
- action deep links.

Fix:
preserve exact source/evidence.
Do not collapse NGT and Varanegar provenance.

### Negin AI
Keep:
- deep AI Workspace,
- authenticated real backend conversation.

Move out of the deep workspace:
- contextual copilot for current module/entity.

Add:
- ambient evidence-backed AI,
- backend Next Best Action read model,
- agent action layer calling canonical capability APIs.

Developer-oriented integrity messaging should be reduced to compact service status or diagnostics.

## 4. Shared UI duplication audit

The user requirement applies to both business capabilities and UI primitives.

### AppHeader
Current canonical shared component exists.

Already shared:
- Home
- Customer360
- Notifications

Still duplicated locally:
- Customers
- Route
- Orders
- Reports

Decision:
**MERGE into one AppHeader**

### BottomDock
Current canonical shared component exists.

Already shared:
- Home
- Customer360
- Notifications

Still duplicated locally:
- Customers
- Route
- Orders
- Reports

Decision:
**MERGE into one BottomDock**

### Feedback states
Shared `FeedbackState` exists.

Custom error/loading/empty implementations still exist in:
- Home
- Customers
- Route
- Orders
- Reports

Decision:
**MERGE**

Business messages remain domain-specific.
Visual/state machinery is shared.

### Bottom sheets
Shared `BottomSheet` exists.

Custom sheet implementations still exist for:
- Route visit outcome,
- Orders route picker,
- Orders customer picker,
- other picker patterns.

Decision:
**MERGE presentation primitive**
while keeping domain-specific content and actions.

### Segmented controls / tabs
Shared `SegmentedControl` exists.

Still custom:
- Orders Products / Catalog / Cart tabs,
- some domain-local segmented patterns.

Decision:
**MERGE primitive**
without merging business states.

### Picker behavior
`VisitorPicker` is already shared and should remain the canonical selection primitive where its interaction model fits.

### QuantityStepper
Orders uses the shared Design System primitive.

Decision:
**KEEP**

### InsightCard
Home uses the shared visual primitive.

Business logic behind it is not yet canonical.

Decision:
**KEEP primitive; MOVE intelligence logic to backend**

## 5. What is not duplication

The same capability may have shallow projections in several contexts.

Example:
Returned cheque:
- Home -> alert
- Customer360 -> badge/summary
- Reports -> aggregate
- Alert Center -> event
- Orders -> credit context
- Finance -> canonical detail

This is valid because only one place owns the full business meaning/workflow.

The same visual component may also be reused in many places.
That is desired reuse rather than duplication.

## 6. Required rebuild order

### Phase 0 — semantic/runtime gates
1. Commercial Intelligence / Next Best Action read model
2. target KPI semantic validation
3. exact alert provenance
4. official NGT EVC connectivity/availability state
5. bounded Cloud/grs telemetry read model
6. preserve final Varanegar commit disabled until verified

### Phase 1 — shared shell cleanup
1. AppHeader everywhere
2. BottomDock everywhere
3. FeedbackState everywhere
4. BottomSheet primitive where interaction matches
5. SegmentedControl where interaction matches

No business behavior changes in this phase.

### Phase 2 — information architecture migration
1. Home / Today
2. Customer360
3. Route / Field Execution
4. Orders / Selling Workspace
5. Reports / Analysis
6. Alert Center
7. Contextual AI across all modules

### Phase 3 — enterprise depth
Preserve but keep role-bounded:
- Warehouse Operations
- Admin / Planning
- Platform / Knowledge

## 7. Build gate

No screen migration should begin until the element being changed has:
- capability ID,
- owner,
- canonical surface,
- source truth,
- availability state,
- allowed projection.

Run:

`python scripts/architecture/validate_capability_registry.py`

and:

`python scripts/architecture/validate_ui_capability_audit.py`

before architecture commits.

This audit changes architecture decisions only.
It intentionally makes no visual/UI code changes.
