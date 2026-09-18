# NeginAI UI/UX Architecture v1 — Inventory-Driven Draft

**Status:** ARCHITECTURE DRAFT — IMPLEMENTATION BASELINE AFTER APPROVAL  
**Date:** 2026-09-18  
**Scope:** Seller / Visitor experience first; reusable platform rules for all NeginAI workspaces  
**Primary target:** Mobile-first RTL PWA / Android-class viewport  
**Design language:** NeginAI Design System v2  
**Architecture inputs:** live system inventory + product-domain architecture + product experience contract

---

# 1. Purpose

This document defines **how NeginAI must behave and feel as an interface** after product domains and source-of-truth boundaries have been identified.

It does not define business truth itself.

The dependency order is:

```
Live Sources
  ↓
Semantic Contracts
  ↓
Backend / Read Models
  ↓
Product Architecture
  ↓
UI/UX Architecture  ← this document
  ↓
Design System Components
  ↓
Frontend Implementation
```

A screen must never invent product architecture, KPI meaning, or business ownership.

---

# 2. Authority order

When UI documents conflict, use this order:

1. Explicit latest approved product decision
2. `NEGINAI_SYSTEM_INVENTORY_2026-09-18.md`
3. `NEGINAI_PRODUCT_ARCHITECTURE_V1_DRAFT.md`
4. `NEGINAI_PRODUCT_EXPERIENCE_CONTRACT.md`
5. This UI/UX Architecture
6. Canonical Design System
7. Master Screen Map
8. Older UX/Foundation drafts
9. Existing implementation

Important consequence:

Older documents that describe Home as a generic KPI dashboard are superseded by the **Commercial Command** model.

---

# 3. Product experience definition

NeginAI is not:

- a dashboard collection,
- a set of cards,
- a chatbot wrapper,
- a skin over Varanegar,
- a long mobile webpage,
- a navigation menu for backend endpoints.

NeginAI is:

> A living, depth-first commercial operating system that turns verified operational data into understanding, urgency, action and execution.

Every Level-0 surface must answer at least one of these questions:

- What changed?
- What matters now?
- What should I do next?
- What is blocking me?
- Where is the opportunity?
- What evidence supports this?

---

# 4. Core UI philosophy

## 4.1 LIVE

The interface visibly responds to:

- data arrival,
- data change,
- current operational state,
- urgency,
- opportunity,
- loading,
- completion,
- error,
- offline/stale conditions.

Living UI is not decorative animation.

A motion without state meaning is noise.

## 4.2 DEPTH

Mobile depth replaces unnecessary page length.

```
L0 — Command / orientation / decision
L1 — Selected domain workspace
L2 — Focused entity or decision context
L3 — Evidence / history / detail
L4 — Transaction confirmation or deep analytical record
```

Not every module needs L4.

Depth must stay inside the owning domain unless the user's job truly changes.

## 4.3 ACTION

Every prominent surface must be one of:

- actionable,
- explanatory,
- navigational into meaningful depth,
- status-only because action is intentionally impossible.

Dead decorative cards are prohibited.

## 4.4 COMMERCIAL PRESSURE

The interface should create healthy motivation and urgency from real evidence:

- target pace when validated,
- missed opportunity,
- active promotion,
- price/reward change,
- stock opportunity,
- high-value inactive customer,
- returned cheque/credit block,
- route execution gap,
- follow-up,
- distribution/return issue,
- commercial alert.

No fake gamification.

No invented performance score.

---

# 5. Global shell

## 5.1 Persistent shell

Seller workspace shell:

```
┌─────────────────────────────┐
│ Brand / Alert / User Context│  Header
├─────────────────────────────┤
│                             │
│        Active Domain        │  Workspace
│                             │
├─────────────────────────────┤
│ Reports Customers Order ... │  Bottom Dock
└─────────────────────────────┘
```

Persistent elements:

- Negin AI identity
- user/seller context
- Alert Center entry
- bottom navigation
- safe-area handling

Module content must not recreate shell controls.

## 5.2 Header

Header owns only:

- brand identity,
- global alerts,
- seller/account context,
- profile access.

It must not contain:

- module filters,
- random quick actions,
- duplicated page titles.

Recommended compact mobile height:
**72–84px including spacing**, depending on safe area.

## 5.3 Bottom Navigation

Seller destinations:

1. Home — Commercial Command
2. Route — Field Execution
3. Order — Selling Workspace
4. Customers — Customer Intelligence
5. Reports — Analysis

Order remains the emphasized central action.

Rules:

- Bottom Nav changes **domain/job**.
- In-module depth does not use Bottom Nav.
- A Route detail must not open Customers merely to show route customers.
- A Customer financial layer must not open Reports merely to show customer-specific finance.
- Bottom-nav state persists while lower layers are open.

---

# 6. Navigation grammar

## 6.1 Domain transition

Use when the user changes jobs.

Examples:

- Home → Route to execute route action
- Customer360 → Orders to create an order
- Alert → Reports for broad historical analysis

This is a true navigation transition.

## 6.2 In-domain depth

Use when the user stays in the same job.

Examples:

```
Route
  → Route plan
    → Route customer
      → Visit

Customers
  → Priority segment
    → Customer
      → Financial detail

Orders
  → Brand
    → Product
      → Order line
        → Preview
```

Prefer:

- layered workspace,
- sheet,
- morph/expand,
- focused depth surface,
- shared-element continuity.

Do not substitute unrelated routes for depth.

## 6.3 Back behavior

Back always returns one semantic layer.

It must never unexpectedly:

- exit the module,
- reset context,
- jump to Home,
- discard a draft.

Draft-discard requires explicit confirmation.

---

# 7. Scroll policy

## 7.1 Level 0

Target: **one viewport when practical**.

Level 0 must not require scroll for its primary decision.

Allowed content:

- current state,
- top opportunity/risk,
- primary next action,
- compact domain entry points.

Prohibited:

- long KPI stacks,
- repeated cards,
- full customer lists,
- full route lists,
- historical detail.

## 7.2 Level 1

Short controlled scroll is acceptable when content is naturally sequential.

Prefer depth over stacking unrelated categories.

## 7.3 Level 2+

Scroll is allowed for:

- customer history,
- catalog,
- route stop lists,
- report details,
- timelines,
- document lines,
- transaction history.

The goal is not “zero scroll everywhere”.

The goal is:
**no accidental scroll caused by poor information architecture.**

---

# 8. Visual language — NeginAI Design System v2

## 8.1 Personality

```
Premium Enterprise
+ Intelligent
+ Operational
+ Calm Futurism
+ Living Tactility
```

Target ratio:

- 65–70% clean enterprise
- 20–25% controlled glassmorphism
- 10–15% soft neumorphism

Glass and Neu are complementary.

Glass communicates:
- layering,
- live context,
- spatial depth,
- overlays.

Neu communicates:
- tactile interaction,
- raised controls,
- inset states,
- physical affordance.

## 8.2 Canvas

Base:
deep blue-black / navy.

Avoid:
- pure black large surfaces,
- grey generic admin UI,
- excessive gradients.

Depth should be visible through:

- tonal separation,
- edge lighting,
- translucent layers,
- controlled shadow,
- spatial offset.

## 8.3 Glassmorphism

Use on:

- command surfaces,
- contextual overlays,
- depth layers,
- Alert Center,
- map overlays,
- bottom dock,
- focused workspace.

Requirements:

- translucent material,
- background separation,
- subtle border,
- limited blur,
- edge highlight.

Do not use glass if the background contains no meaningful depth behind it.

## 8.4 Neumorphism

Use on:

- primary tactile controls,
- segmented controls,
- quantity controls,
- raised operational actions,
- selected/pressed states,
- small command pads.

Dark neumorphism must use restrained dual-depth lighting.

Never reduce contrast for aesthetics.

## 8.5 Gold

Gold represents:

- primary hierarchy,
- branded action,
- focus,
- selected primary destination,
- premium emphasis.

Gold does **not** mean success or warning.

Semantic states keep their own colors.

---

# 9. Typography contract

Primary Persian font:
**Vazirmatn**

Latin:
Inter/system only where needed.

## Minimum mobile sizes

- page/domain title: **22–26px**
- important action/title: **16–18px**
- default body: **14–16px**
- secondary body: **13–14px**
- label: **12–13px**
- metadata: **11–12px**

Anything below 11px is prohibited for normal operational content.

User feedback has repeatedly identified tiny typography as a product defect.

## Rules

- max 3 typography levels inside one surface
- values and labels must not compete
- critical data never uses low-contrast tiny text
- Persian digits preferred except technical IDs
- mixed Persian/English direction must be explicitly controlled

---

# 10. Density

NeginAI should feel **information-rich, not crowded**.

Three density modes:

### Comfortable
Login, confirmations, onboarding.

### Standard
Home, Customer360, Route command layers.

### Dense
Catalogs, route lists, financial records, reports.

Do not solve space problems by shrinking font.

Solve with:
- grouping,
- progressive disclosure,
- depth,
- abbreviated secondary metadata,
- contextual detail.

---

# 11. Living UI state model

Canonical living states:

- ambient
- live
- updating
- changed
- attention
- urgent
- opportunity
- active
- completed
- error
- stale/offline

## Examples

### New price change
Subtle changed reaction → Alert Center category “قیمت فروش”.

### Critical returned cheque
Attention cue, not permanent flashing.

### Stock becomes available
Opportunity energy cue.

### Route stop completed
State morph + progress update.

### Order preview calculating
Skeleton/live calculation state.

### Successful save
Compact completion transition.

## Motion limits

- touch feedback: 90–160ms
- micro state: 160–240ms
- panel transition: 220–360ms
- ambient: 4–12s, extremely subtle

No permanent bouncing.

No decorative particle field in operational screens.

Respect:
`prefers-reduced-motion`.

---

# 12. Material + motion relationship

Material and motion must work together.

Example:

```
Idle glass surface
    ↓ press
Neu inset response
    ↓ open
Depth surface moves forward
    ↓ data refresh
Changed edge reaction
```

A static glossy card is not Living UI.

An animated flat card is not spatial UI.

---

# 13. Home — Commercial Command

## Job

> Tell me what matters now and move me toward better commercial execution.

Home is not:

- a route dashboard,
- a reports dashboard,
- a customer list,
- an ERP summary page.

## L0 composition

Target mobile fold:

```
┌──────────────────────────┐
│ Live Commercial State    │
│ Seller / time / momentum │
├──────────────────────────┤
│ NEXT BEST ACTION         │
│ evidence + action        │
├─────────────┬────────────┤
│ Opportunity │ Risk       │
├─────────────┼────────────┤
│ Operations  │ Intelligence│
└─────────────┴────────────┘
```

The above is conceptual—not a mandatory card grid.

The visual implementation should prefer one connected control surface rather than four unrelated dashboard cards.

## Home data

Potential inputs:

- Commercial Intelligence read model
- validated target status
- alerts
- current route status
- open invoice/returned cheque risk
- stock/commercial opportunity
- price/promo change
- distribution state

## Motivation

Examples:

- “۳ مشتری با فرصت فروش تأییدشده”
- “برند X موجودی فعال + طرح جاری”
- “فاصله تا pace هدف” only if semantically validated

## Urgency

Examples:

- credit block
- returned cheque
- critical commercial price change
- route execution miss
- unresolved high-severity alert

## Home depth

L1:
- Performance
- Opportunity
- Risk
- Operations

L2:
supporting evidence.

Then explicit action can transition to owning module.

---

# 14. Route — Field Execution

## Job

> Where do I go next, what should I do at this stop, and what is the state of today's field execution?

## L0

Working day:
- map dominant
- current/next stop
- route progress
- current execution state
- primary action

Non-working day:
- route calendar state
- assigned routes
- preparation context

## Depth

```
L0 Route map / execution
  ↓
L1 Route stops
  ↓
L2 Selected stop
  ↓
L3 Visit workspace
```

Route customers remain inside Route depth.

Do not navigate to Customers module merely to list them.

## Map

Use overlays instead of page stacks:

- map controls,
- selected stop sheet,
- navigation action,
- route mode,
- list drawer.

Map should remain spatial anchor whenever execution is active.

## Selected stop

Must expose:

- customer identity
- distance/location
- relevant risk
- visit state
- quick contact
- start visit

Not full Customer360.

---

# 15. Customers — Customer Intelligence

## Job

> Who should I understand, sell to, follow up, or protect?

## L0

Not a raw list.

Use decision categories such as:

- priority/opportunity
- needs follow-up
- financial risk
- active/current route context
- all

Only categories backed by real data should exist.

## Depth

```
L0 Decision categories
  ↓
L1 Customer list
  ↓
L2 Customer360
  ↓
L3 Sales / Finance / Visit / History
```

## Customer360 L0

Above the fold:

- customer identity
- commercial state
- financial warning if relevant
- recent relationship signal
- primary actions

Actions:
- call
- route/navigation
- visit
- order

Only enabled when capability/state allows.

## Financial depth

Use:
- per-customer open invoices
- balance
- returned cheque
- settlement/cardex detail

Do not duplicate Reports module for customer-specific finance.

---

# 16. Orders — Selling Workspace

## Job

> What can I sell now, under what real commercial conditions, and how do I safely complete the request?

## Context first

Orders should know:

- selected customer if present,
- seller catalog scope,
- warehouse,
- order type,
- payment context.

## L0

- current customer context
- commercial readiness
- search/discovery
- opportunity/stock cues
- cart state

## Depth

```
L0 Selling context
  ↓
L1 Brand / Group / Search results
  ↓
L2 Product detail / quantity
  ↓
L3 Order draft
  ↓
L4 Official preview / completion
```

## Product card

Prefer spatial/tactile behavior:

Front:
- product image
- name
- stock
- commercial hint

Back/detail:
- quantity
- unit
- line controls
- active rule context

Do not force user to switch repeatedly between catalog and cart.

## Truth states

Must distinguish visually:

- local draft
- saved request
- official preview available
- preview unavailable
- credit blocked
- final ERP submission unavailable
- final ERP submission verified

Never imply final order success without verified ERP order number.

---

# 17. Reports — Analysis

## Job

> Why is this happening and where should I investigate?

## L0

Start from analytical questions/domains:

- Sales
- Finance / Receivables
- Returns
- Distribution
- Inventory
- Profitability

Do not start from dozens of KPI cards.

## Depth

```
L0 Domain/question
  ↓
L1 Summary/diagnosis
  ↓
L2 Breakdown
  ↓
L3 record/document detail
```

Long scrolling is allowed at detailed analytical levels.

Tables must support dense mode.

---

# 18. Alert Center

Global surface.

## Purpose

> What changed that requires my awareness or action?

## Categories

- price
- discount/reward
- finance
- credit
- route
- customer
- distribution
- return
- general operational

## Every alert must show

- severity,
- category,
- title,
- concise evidence,
- time,
- read state,
- acknowledgment requirement if applicable,
- action path.

## Severity

Critical:
immediate operational/financial blocker.

High:
important commercial change/action.

Medium:
meaningful but non-blocking.

Info:
awareness.

Do not rely on color alone.

---

# 19. Negin AI contextual layer

Negin AI is not primarily a standalone chat destination.

It is a contextual intelligence surface.

Context examples:

Home:
“Why is this the Next Best Action?”

Customer:
“Analyze this customer's opportunity/risk.”

Route:
“Why is this stop important?”

Order:
“Explain this price/rule/restriction.”

Reports:
“Explain this change.”

Dedicated AI workspace still exists for free-form analysis.

---

# 20. Login

Login should communicate:

- premium enterprise identity,
- trust,
- intelligence,
- restrained living material.

Allowed:
subtle fluid/ambient brand motion.

Not allowed:
large distracting animation,
gaming visual language,
fake recovery actions.

Primary task remains authentication.

---

# 21. Global system states

Every major module must have designed states for:

- loading,
- skeleton,
- empty,
- partial data,
- stale data,
- offline,
- error,
- retry,
- unauthorized,
- session expired,
- success,
- blocked capability.

Empty ≠ blank space.

An empty state must explain:
- what is absent,
- why if known,
- what user can do.

---

# 22. Data confidence and semantic status

UI must visually distinguish:

- Canonical fact
- Validated fact
- Pending validation
- Inferred/assistive insight
- Unavailable

Example:

Target KPI semantic not validated:

Do:
“هدف فروش — در حال اعتبارسنجی”

Do not:
show fake percentage ring.

AI recommendation:
must be presented as recommendation/evidence, not ERP truth.

---

# 23. Component rules

Prefer shared primitives.

Core surface families:

- Stage Surface
- Layer Surface
- Detail Surface
- Portal / Depth Entry
- Operational Row
- Entity Header
- Action Dock
- Context Strip
- Alert Item
- State Banner
- Bottom Sheet
- Full-screen depth layer

A new component is justified only if existing primitives cannot represent the interaction.

No screen-specific “one-off design system”.

---

# 24. Touch / tactile behavior

Minimum hit target:
**44 × 44px**

Primary:
48–52px where practical.

Pressed state must be visible.

Tactile model:

- raised → press → inset
- selected → stable semantic emphasis
- disabled → clearly unavailable
- loading → action remains spatially anchored

Do not make invisible click zones.

---

# 25. Responsive architecture

## 320–389
Compact mobile:
- preserve hierarchy
- reduce secondary text
- never shrink primary body below minimum

## 390–767
Primary seller target.

## 768–1199
Expand spatial depth and side-by-side detail.

## 1200+
May use workspace split views.

Do not create a different product architecture for desktop.

---

# 26. RTL rules

Persian is primary.

- layout direction RTL
- progress semantics remain logically correct
- navigation arrows reflect direction intentionally
- technical IDs/LTR values isolated
- money/quantity strings must not visually reorder
- map controls may follow map-industry conventions where appropriate

Mixed-direction text must be explicitly tested.

---

# 27. Performance rules

Living UI must not make field work slower.

Targets:

- avoid continuous large blur animation
- animate transform/opacity where possible
- pause nonessential ambient motion when hidden
- skeleton before delayed content
- warm critical order context where backend supports it
- use product image lazy loading
- map overlays should not force full map rerender

Lower-end Android must remain usable.

---

# 28. Accessibility

Required:

- semantic labels
- focus-visible
- non-color state indicators
- reduced motion
- readable contrast
- 44px targets
- text scaling resilience
- screen reader labels for icon-only controls

Enterprise polish without accessibility is not accepted.

---

# 29. Module-to-data UI mapping

| UI module | Primary UI source/read model |
|---|---|
| Home | Commercial Intelligence + validated Seller Workspace facts |
| Route | NGT route/visit + Neshan + future field telemetry |
| Customers | NGT/GNR + customer-scoped ERP finance/sales |
| Orders | NGT catalog/context + stock + EVC + controlled app state |
| Reports | semantic Varanegar reporting routes |
| Alerts | Operational Notification/Event layer |
| AI | contextual backend reasoning over current scope |

---

# 30. Anti-patterns — prohibited

- Generic 2×2 dashboard grid as default architecture
- Blank premium-looking space without purpose
- 10px operational body text
- Dead cards
- Module shortcut duplicated inside another module
- “Depth” implemented as unrelated page navigation
- Fake toggles
- Fake KPI
- Fake backend success
- Animation without state meaning
- Excessive glow
- permanent pulsing
- glass on every surface
- gold everywhere
- long Home scroll
- large headings that consume the fold
- native controls visually inconsistent with Design System
- copying screenshot content from visual references

---

# 31. Seller Level-0 fold targets

Approximate target on 390×844 class device after browser/PWA chrome:

## Home
- commercial state
- Next Best Action
- opportunity/risk/operation signal
- no primary scroll

## Route
- map/current route state
- next stop / action
- no primary scroll

## Customers
- decision categories + high-priority entry
- list only after category selection or lower region

## Orders
- customer/commercial context + discovery + cart state
- catalog scroll starts intentionally

## Reports
- analytical domains/questions
- detail after selection

---

# 32. Depth transition specification

A depth transition must communicate:

**“I stayed in the same domain and moved closer to detail.”**

Visual cues may include:

- parent surface recedes,
- selected element expands/morphs,
- lower layer gains elevation,
- persistent context remains visible,
- back affordance appears.

A module transition must communicate:

**“My job changed.”**

Use stronger workspace replacement.

Do not over-animate either.

---

# 33. Home emotional outcome

Home should create three simultaneous feelings:

## Control
“I know my current commercial state.”

## Motivation
“I can see where the next gain is.”

## Urgency
“I know what I should not ignore.”

These feelings must emerge from data hierarchy and interaction, not motivational slogans.

---

# 34. Visual QA checklist

Every screen must pass:

### Identity
- NeginAI visual DNA recognizable?
- same shell/material system?

### Hierarchy
- one obvious primary purpose?
- top action/state visible?

### Depth
- detail separated into lower layers?
- no unnecessary long Level-0 stack?

### Living
- loading/change/attention/action states visible?
- motion semantic?

### Tactility
- controls look and feel interactive?
- press states?

### Truth
- real capability?
- real data?
- semantic status honest?

### Readability
- body size acceptable?
- contrast?
- RTL correct?

### Performance
- no heavy decorative animation?
- no layout jank?

---

# 35. Implementation gate

Before changing a page, developer/designer must write:

```
DOMAIN:
USER JOB:
LEVEL:
SOURCE DATA:
PRIMARY ACTION:
SECONDARY ACTIONS:
DEPTH DESTINATIONS:
SCROLL POLICY:
LOADING STATE:
EMPTY STATE:
ERROR STATE:
LIVING TRIGGERS:
SEMANTIC RISKS:
```

If these are unclear, implementation must not start.

This gate exists specifically to prevent visual patching without architecture.

---

# 36. Migration sequence from current vNext

No full rewrite.

## Phase 0 — Freeze random visual edits
Do not continue page-by-page decoration.

## Phase 1 — Stabilize Design Primitives
Map current CSS/components to canonical primitives.

## Phase 2 — Commercial Intelligence contract
Create backend/read model before rebuilding Home.

## Phase 3 — Home
Rebuild Commercial Command from real data.

## Phase 4 — Route
Normalize map-first execution and real in-module depth.

## Phase 5 — Customers
Decision categories → Customer360 → detail.

## Phase 6 — Orders
Complete sellable discovery, imagery, official preview states.

## Phase 7 — Reports
Question/domain-first analysis.

## Phase 8 — Global surfaces
Alert Center / AI / Profile.

## Phase 9 — Living polish
Only after product architecture is stable:
- morph,
- state reactions,
- glass depth,
- tactile material,
- microinteraction consistency.

---

# 37. Figma structure recommendation

```
00 — Foundations
01 — Tokens
02 — Components
03 — Patterns
04 — Shell
05 — Home
06 — Route
07 — Customers
08 — Customer360
09 — Orders
10 — Reports
11 — Alerts
12 — AI
13 — Auth/Profile
90 — States
99 — Archive
```

For each module:

- L0
- L1
- L2
- L3 where applicable
- Loading
- Empty
- Error
- Critical
- Opportunity
- Reduced-motion notes

---

# 38. Definition of Done — UI

A seller-facing screen is not done until:

- product domain ownership is correct,
- source data is real,
- semantic status is honest,
- mobile 390 works,
- RTL is correct,
- primary fold is intentional,
- depth is meaningful,
- scroll policy is respected,
- typography passes minimum sizes,
- Design System primitives are reused,
- loading/empty/error exist,
- touch feedback exists,
- Living triggers are defined,
- reduced motion works,
- feature behavior is preserved,
- backend capability is not faked,
- visual QA is performed on a real phone.

---

# 39. Canonical seller journey

```
LOGIN
  ↓
HOME — What matters now?
  ├── Opportunity → CUSTOMER / ORDER
  ├── Risk → CUSTOMER FINANCE / REPORT
  ├── Execution → ROUTE
  └── Change → ALERT CENTER

ROUTE — What do I do next?
  ↓
STOP
  ↓
VISIT
  ↓
ORDER / OUTCOME

CUSTOMERS — Who needs attention?
  ↓
CUSTOMER 360
  ├── ORDER
  ├── VISIT
  ├── FINANCE
  └── HISTORY

ORDERS — What can I sell?
  ↓
CATALOG
  ↓
DRAFT
  ↓
OFFICIAL PREVIEW
  ↓
SAVE / VERIFIED SUBMIT

REPORTS — Why is this happening?
  ↓
ANALYSIS
  ↓
EVIDENCE
```

---

# 40. Final principle

The interface must never start with:

> “What cards can we put here?”

It must start with:

> “What decision or action does this user need at this moment, what verified data supports it, and how deep should they go before changing jobs?”

That is the canonical UI architecture for NeginAI v1.
