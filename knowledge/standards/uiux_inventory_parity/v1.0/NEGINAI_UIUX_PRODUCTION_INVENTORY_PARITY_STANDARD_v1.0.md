# NeginAI UI/UX Production Inventory + Feature Parity Standard v1.0

## 0. هدف

این سند کنترل مرکزی برای جلوگیری از این خطاست:

> «صفحه زیباست، ولی یک قابلیت، state، action، role rule یا business context از نسخه واقعی NeginAI جا افتاده.»

این استاندارد باید در تمام مراحل زیر استفاده شود:

`Source Audit → Runtime/UI Audit → Canonical Inventory → Screen Contract → Image Generation → Figma Systemization → Prototype → Code Mapping → Runtime QA → Feature Parity`

---

# 1. Source Authority برای UI/UX

برای هر آیتم طراحی، منبع باید ثبت شود.

ترتیب پیشنهادی Evidence:

1. تصمیم صریح جدید مالک پروژه
2. Master Project Map / Project Authority
3. UI/UX Baseline / Figma Handoff
4. Runtime واقعی NeginAI
5. Live repository evidence
6. Business/Semantic contract
7. Golden/reference screenshots
8. Design inference
9. General UX knowledge

**Design inference هرگز نباید Capability جدید را به‌صورت FACT وارد محصول کند.**

---

# 2. شناسه‌گذاری Canonical

## Module ID
```text
mod.<domain>
```

نمونه:
```text
mod.shell
mod.ai
mod.seller
mod.route
mod.customer
mod.previsit
mod.ordering
mod.reports
mod.planning
mod.control
mod.organization
mod.warehouse
mod.notifications
mod.automation
mod.settings
```

## Screen ID
```text
scr.<module>.<screen>
```

نمونه:
```text
scr.route.daily_overview
scr.route.full_map
scr.customer.profile_360
scr.ordering.catalog
scr.ordering.cart
scr.ordering.preview
```

## Component ID
```text
cmp.<family>.<name>
```

نمونه:
```text
cmp.nav.bottom
cmp.customer.summary_card
cmp.route.stop_card
cmp.order.quantity_stepper
cmp.ai.composer
```

## Action ID
```text
act.<domain>.<verb>
```

نمونه:
```text
act.route.start
act.route.recenter
act.customer.call
act.customer.navigate
act.order.save_draft
act.order.preview
act.order.submit
```

## State ID
```text
st.<domain>.<state>
```

نمونه:
```text
st.order.draft
st.order.submitting
st.order.sent
st.order.failed
st.app.offline
st.permission.denied
```

## Entity ID
```text
ent.<domain>.<entity>
```

نمونه:
```text
ent.route.tour
ent.route.stop
ent.customer.account
ent.order.draft
ent.order.receipt
ent.inventory.stock_context
```

---

# 3. Module Inventory Template

برای هر Module یک رکورد:

| Field | مقدار |
|---|---|
| Module ID | `mod.xxx` |
| نام فارسی | |
| Product role | |
| Primary roles | |
| Entry points | |
| Parent navigation | |
| Child screens | |
| Core entities | |
| Primary workflows | |
| External dependencies | |
| Permissions | |
| Mobile priority | High / Medium / Low |
| Desktop priority | High / Medium / Low |
| Business criticality | Critical / High / Normal |
| Source evidence | |
| Runtime evidence | |
| Inventory status | CONFIRMED / PARTIAL / OPEN |
| Design status | NOT_STARTED / DRAFT / QA / APPROVED |
| Runtime parity | PENDING / PASS / FAIL / BLOCKED |

---

# 4. Screen Inventory Template

هر Screen/Surface باید دقیقاً این فیلدها را داشته باشد:

| Field | توضیح |
|---|---|
| Screen ID | شناسه یکتا |
| نام | |
| Module | |
| Surface type | Page / Panel / Modal / Sheet / Drawer / Overlay / State |
| Role | Seller / Supervisor / Manager / Admin / Shared |
| Entry point | کاربر از کجا وارد می‌شود |
| Navigation origin | Bottom Nav / Modules / Context / Deep link / Action |
| Exit/back behavior | |
| Primary goal | |
| Primary action | |
| Secondary actions | |
| Destructive actions | |
| Required data | |
| Core entities | |
| Required components | |
| Required states | |
| Permission behavior | |
| Offline behavior | |
| Mobile behavior | |
| Tablet behavior | |
| Desktop behavior | |
| Accessibility requirements | |
| Runtime source | |
| Code source | |
| Existing UX issues | |
| Target UX improvement | |
| Mandatory elements | |
| Optional elements | |
| Forbidden invention | |
| Visual reference | |
| Design status | |
| Parity status | |

---

# 5. Entity Inventory Template

| Entity ID | نام | Module | نمایش در کدام Screens | Critical fields | Editable? | Source | Semantic status |
|---|---|---|---|---|---|---|---|
| `ent.customer.account` | مشتری | Customer | | | | | |
| `ent.route.stop` | توقف مسیر | Route | | | | | |
| `ent.order.draft` | پیش‌نویس سفارش | Ordering | | | | | |

قانون:
**UI نباید Entityهای Business را merge کند فقط چون از نظر بصری شبیه‌اند.**

مثلاً:
- planned route ≠ actual visit sequence
- local order intent ≠ ERP accepted order
- on-hand ≠ available ≠ reserved ≠ sellable stock

---

# 6. Component Inventory Template

| Component ID | Family | نقش | Screens | Variants | States | Size rules | RTL | A11y | Figma status | Code status |
|---|---|---|---|---|---|---|---|---|---|---|
| `cmp.nav.bottom` | Navigation | Main shell | | | | | Yes | | | |
| `cmp.ai.composer` | AI | Input | | | | | Yes | | | |
| `cmp.route.stop_card` | Route | Operational | | | | | Yes | | | |
| `cmp.order.quantity_stepper` | Ordering | Control | | | | | Yes | | | |

برای Componentهای اصلی باید mapping زیر وجود داشته باشد:

```text
Figma Component
↕
Semantic Tokens
↕
States/Variants
↕
Responsive behavior
↕
Frontend counterpart
```

Status:
```text
FIGMA_ONLY
CODE_ONLY
BOTH_MISMATCHED
MAPPED_CONFIRMED
OPEN
```

---

# 7. Action Inventory Template

| Action ID | Screen | Trigger | Result | Permission | Confirmation | Failure state | Idempotency-sensitive? | Evidence |
|---|---|---|---|---|---|---|---|---|

برای مسیرهای تجاری:
- save draft
- submit
- retry
- reconcile
- cancel
- approve

نباید صرفاً به یک Button زیبا تقلیل داده شوند؛ State contract لازم است.

---

# 8. State Inventory Template

## Global states
```text
default
hover
focus
selected
active
disabled
loading
empty
error
offline
success
warning
destructive
permission_denied
```

## Business-sensitive states
```text
draft
prepared
submitting
submitted
accepted
failed
ambiguous
reconciled
cancelled
```

هر State باید این موارد را تعریف کند:

| Field | مقدار |
|---|---|
| State ID | |
| Trigger | |
| UI feedback | |
| Allowed actions | |
| Forbidden actions | |
| Recovery action | |
| Audit requirement | |
| Source evidence | |

---

# 9. Role / Permission Matrix Template

| Capability ID | Seller | Supervisor | Manager | Admin | Permission key | Visibility rule | Action rule |
|---|---:|---:|---:|---:|---|---|---|

قاعده Shell:
**Role تفاوت Capability visibility/authorization ایجاد می‌کند، نه Navigation architecture کاملاً متفاوت.**

---

# 10. Feature Parity Matrix

این جدول Gate اصلی جلوگیری از جاافتادگی است.

| ID | Module | Screen | Type | Source evidence | Runtime seen | Inventory | Target image | Figma | Prototype | Code | Runtime vNext | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|

Type:
```text
SCREEN
COMPONENT
ACTION
STATE
ENTITY
ROLE_RULE
BUSINESS_CONTEXT
```

Verdict:
```text
PASS
MISSING_IN_DESIGN
MISSING_IN_INVENTORY
MISSING_IN_RUNTIME
NEEDS_VALIDATION
INFERRED
BLOCKED
NOT_APPLICABLE
```

## Gate Rule
```text
Mandatory missing > 0  => FAIL
Unknown business semantics > 0 => BLOCKED
Visual mismatch only => QA
All mandatory mapped + tested => PASS
```

---

# 11. Screen Contract

هیچ تصویر Hi-Fi بدون Contract ساخته نشود.

Contract هر Screen باید شامل:

1. Screen ID
2. Product goal
3. User role
4. Entry point
5. Exit/back behavior
6. Mandatory elements
7. Mandatory actions
8. Mandatory entities
9. Mandatory states
10. Permission behavior
11. Offline behavior
12. Responsive behavior
13. Accessibility gates
14. Business invariants
15. Source evidence
16. Visual direction
17. Forbidden inventions
18. Acceptance tests

---

# 12. Image Generation Contract

هر Prompt تصویر باید چهار بخش داشته باشد:

## A. Visual DNA
```text
Modern Enterprise
70% clean enterprise
20% mild glassmorphism
10% soft neumorphism
Dark navy foundation
Muted premium gold
Persian RTL
Mobile-first
Enterprise credibility
```

## B. Mandatory UI Elements
لیست دقیق و غیرقابل حذف.

## C. Functional Constraints
مثلاً:
```text
Do not remove any mandatory action.
Do not invent business rules.
Do not merge distinct business states.
Preserve shared bottom navigation.
Role changes visibility, not shell architecture.
```

## D. Output intent
```text
Production-realistic screen concept
Not a generic dashboard
Not a decorative mockup
Must be implementable
```

---

# 13. Structure Pass → Beauty Pass

## Pass 1 — Structure Fidelity
بررسی:
- Screen goal
- all mandatory components
- all actions
- hierarchy
- navigation
- information architecture
- state exposure
- role context

**اگر Structure PASS نشد، Beauty Pass ممنوع.**

## Pass 2 — Visual Excellence
بررسی:
- typography
- spacing
- hierarchy
- glass intensity
- neumorphism intensity
- contrast
- component consistency
- Persian readability
- visual delight
- production realism

---

# 14. Module Production Gate

هر Module فقط زمانی وارد Module بعدی شود که:

```text
Inventory Coverage        PASS
Screen Contracts          PASS
Image Structure Review    PASS
Visual QA                 PASS
Feature Parity            PASS or explicitly BLOCKED with evidence
Neutral User Journey      PASS
Responsive Review         PASS
Accessibility Review      PASS
Figma Mapping             PASS/PARTIAL with known gaps
```

---

# 15. Neutral User Acceptance Gate — NUAG

یک فرد بی‌طرف باید بتواند بدون دانستن پیاده‌سازی:

1. Feature را پیدا کند
2. وارد Screen درست شود
3. مفهوم صفحه را بفهمد
4. Primary task را تکمیل کند
5. اشتباه کند و recover کند
6. Back/Close را بفهمد
7. Loading/Error/Empty را بفهمد
8. در موبایل با یک دست کار کند
9. در Desktop workflow را گم نکند

Verdict:
```text
PASS
FAIL
BLOCKED
```

---

# 16. Design QA Checklist

برای هر Screen:

```text
[ ] Screen Contract exists
[ ] Mandatory elements complete
[ ] Mandatory actions complete
[ ] Required business entities visible
[ ] Required states defined
[ ] Role context correct
[ ] Shared navigation preserved
[ ] Back/Close behavior defined
[ ] Loading defined
[ ] Empty defined
[ ] Error defined
[ ] Offline defined where relevant
[ ] Permission denied defined
[ ] Touch target >= 44px
[ ] Focus state defined
[ ] Color is not the only state signal
[ ] Persian/RTL verified
[ ] Long text considered
[ ] 390px mobile tested
[ ] 768px tablet considered
[ ] 1440px desktop considered
[ ] No invented business rule
[ ] Feature Parity row updated
[ ] Runtime validation status recorded
```

---

# 17. Business-Sensitive UI Gate

برای Seller / Visit / Ordering / Inventory / Finance:

UI حق ندارد بدون verified source این موارد را تعیین یا تغییر دهد:

- GPS threshold
- quantity conversion
- carton/unit conversion
- price precedence
- discount stacking
- gift/prize eligibility
- tax order/base
- credit approval
- order acceptance
- inventory concept
- route optimization constraints

هر مورد ناشناخته:

```text
OPEN
NEEDS_VALIDATION
```

نه FACT.

---

# 18. Figma Mapping Contract

بعد از تأیید Screen:

```text
Screen Contract
↓
Figma Frame
↓
Component Instances
↓
Variables/Tokens
↓
Variants/States
↓
Responsive rules
↓
Prototype links
↓
Code counterpart
↓
Visual QA screenshot
```

هر صفحه باید این metadata را داشته باشد:

```text
screen_id
module_id
design_version
inventory_version
parity_status
runtime_status
owner
last_review
```

---

# 19. Naming Convention پیشنهادی در Figma

```text
Screen / Route / DailyOverview
Screen / Customer / Customer360
Screen / Ordering / Catalog
Screen / Ordering / Cart
Screen / Ordering / Preview

Pattern / Route / StopFlow
Pattern / Ordering / PricingSummary

Component / Navigation / BottomItem
Component / Customer / SummaryCard
Component / Product / ProductRow
Component / AI / Composer

State / Global / Offline
State / Ordering / SubmitFailed
```

---

# 20. Versioning

هر خروجی مهم:

```text
Inventory: INV-x.y
Screen Contract: SC-x.y
Design: DS-x.y
Parity Matrix: FP-x.y
Runtime QA: RQ-x.y
```

نمونه:
```text
INV-1.0
SC-route-daily-1.0
DS-route-daily-1.2
FP-1.3
RQ-route-daily-0.1
```

اگر Capability جدید کشف شد:
**Inventory version باید بالا برود.**

---

# 21. قانون تکمیل

```text
NO EVIDENCE → NO COMPLETE
```

یک Screen ممکن است:
- VISUALLY_COMPLETE باشد
- FIGMA_COMPLETE باشد

ولی تا Runtime/Parity اثبات نشده:

```text
PRODUCT_COMPLETE = FALSE
```

---

# 22. Workflow رسمی پیشنهادی

```text
Inspect Source
→ Inspect Runtime
→ Update Inventory
→ Assign IDs
→ Create Screen Contract
→ Structure Prompt
→ Generate Image
→ Structure QA
→ Beauty QA
→ Figma Systemization
→ Prototype
→ Code Mapping
→ Runtime Compare
→ Feature Parity
→ NUAG
→ APPROVED
```

---

# 23. Definition of Done برای تصویر

یک تصویر تنها وقتی `IMAGE_APPROVED` است که:

```text
Mandatory UI coverage = 100%
Unknown mandatory item = 0
Invented business rule = 0
Visual DNA adherence = PASS
Hierarchy = PASS
RTL = PASS
Implementability = PASS
Parity trace = present
```

---

# 24. Definition of Done برای Module

```text
All screens inventoried
All mandatory actions inventoried
All states inventoried
All role rules inventoried
All screen contracts exist
All target images reviewed
Figma structure exists
Critical prototype paths exist
Feature parity has no mandatory missing items
NUAG passed
Responsive/A11y reviewed
Runtime gaps explicitly listed
```
