# NeginAI Canonical Design System v1.0

**Status:** CANONICAL BASELINE â€” APPROVED DIRECTION, EVOLVABLE BY VERSIONING  
**Date:** 2026-09-10  
**Scope:** NeginAI / NeginAI-CORE â€” Web / PWA / Android responsive UI  
**Purpose:** غŒع© ظ…ط±ط¬ط¹ ظˆط§ط­ط¯ ط¨ط±ط§غŒ ط¸ط§ظ‡ط±طŒ ط§ط¨ط¹ط§ط¯طŒ ط±ظپطھط§ط± ط¨طµط±غŒطŒ statesطŒ responsive behavior ظˆ mapping طھظ…ط§ظ… ط¢ط¨ط¬ع©طھâ€Œظ‡ط§غŒ ط±ط§ط¨ط· ع©ط§ط±ط¨ط±غŒ NeginAI.

## 1) Source Authority

### Visual Source of Truth
- ظ…ط¬ظ…ظˆط¹ظ‡ `NEGINAI_ALL_UI_IMAGES_TO_DATE_20260906.zip` ط´ط§ظ…ظ„ 67 طھطµظˆغŒط±: 4 Reference ط§ظˆظ„غŒظ‡ + 63 طھطµظˆغŒط± طھظˆظ„غŒط¯ط´ط¯ظ‡.
- طھطµط§ظˆغŒط± ظپظ‚ط· ظ…ط±ط¬ط¹ **Visual DNA / Quality / Composition / Density / Surface Treatment / Hierarchy / Color / Depth / Motion Feel** ظ‡ط³طھظ†ط¯.
- ظ‡غŒع† ظ…طھظ†طŒ KPIطŒ MissionطŒ LeaderboardطŒ ProductطŒ CustomerطŒ Workflow غŒط§ Business Rule ط§ط² طھطµظˆغŒط± Canonical Content ظ…ط­ط³ظˆط¨ ظ†ظ…غŒâ€Œط´ظˆط¯.

### Content / Behavior Source of Truth
1. ط¢ط®ط±غŒظ† طھطµظ…غŒظ… طµط±غŒط­ ظ…ط§ظ„ع© ظ¾ط±ظˆعکظ‡
2. NeginAI Master Project Map / Project Authority
3. UI/UX Baseline / Figma Design System
4. `VARANEGAR_SEMANTIC_SOURCE_CHATGPT.md`
5. Contractظ‡ط§غŒ Backend / Runtime Evidence

**Canonical Rule:**  
> Images define how NeginAI should look. Project Map defines what NeginAI must contain and how it must work.

---

# 2) Visual DNA

## 2.1 Personality
**Premium Enterprise + Intelligent + Operational + Calm Futurism**

طھط±ع©غŒط¨ ظ‡ط¯ظپ:
- 70% Clean Enterprise
- 20% Mild Glassmorphism
- 10% Soft Neumorphism

### ظ…ظ…ظ†ظˆط¹
- Gaming / Cyberpunk
- Neon-heavy
- Generic admin template
- Overly glossy / chrome
- Cartoonish
- Card-everything layout
- Gold as large flat decorative mass

## 2.2 Recurring Visual Characteristics
- Dark navy canvas with layered blue-black surfaces
- Muted warm gold for primary action, focus and premium emphasis
- Emerald / Cyan / Blue / Amber / Red only for semantic states
- Thin low-contrast borders
- Low-radius glow, never continuous neon outline
- High information density without crowding
- Strong grouping by surface, spacing and typography rather than heavy separators
- Compact mobile-first operational layouts
- Persistent bottom navigation with emphasized AI action
- Rounded geometry, but not toy-like
- Subtle depth through 1â€“3 elevation layers

---

# 3) Foundation Tokens

## 3.1 Color â€” Base
| Token | Value | Usage |
|---|---|---|
| `color.bg.canvas` | `#090E1A` | app canvas |
| `color.bg.canvasRaised` | `#0B1321` | raised app zones |
| `color.surface.1` | `#0E1525` | cards / panels |
| `color.surface.2` | `#121C2E` | elevated cards / sheets |
| `color.surface.3` | `#18243A` | selected / strong surface |
| `color.surface.glass` | `rgba(18,28,46,.72)` | controlled glass |
| `color.border.subtle` | `rgba(154,177,210,.14)` | default border |
| `color.border.strong` | `rgba(154,177,210,.26)` | emphasized border |
| `color.text.primary` | `#F4F6FA` | primary text |
| `color.text.secondary` | `#B5C0D1` | secondary text |
| `color.text.tertiary` | `#7F8CA2` | metadata |
| `color.text.inverse` | `#111722` | text on gold/bright |
| `color.gold.500` | `#D99712` | canonical primary |
| `color.gold.400` | `#E5B33D` | hover/highlight |
| `color.gold.300` | `#F1CD72` | soft accent / glow |
| `color.gold.muted` | `rgba(217,151,18,.16)` | gold tint surface |
| `color.success` | `#2ED47A` | positive / healthy |
| `color.info` | `#36B9E8` | info / AI / neutral data |
| `color.warning` | `#F0B64D` | caution |
| `color.danger` | `#EF5B63` | destructive / critical |
| `color.ai` | `#6EC8FF` | AI-specific secondary accent |

**Rule:** Gold = primary hierarchy, not status. Status colors never replace gold as brand hierarchy.

## 3.2 Typography
Primary Persian/UI font: **Vazirmatn**.  
Latin companion: Inter/System only where needed.  
Persian numerals preferred in Persian UI except immutable IDs / technical codes.

| Token | Size / Line | Weight | Usage |
|---|---|---|---|
| `type.display` | 32/44 | 700â€“800 | hero / auth only |
| `type.h1` | 26/38 | 700 | screen title |
| `type.h2` | 22/34 | 700 | section title |
| `type.h3` | 18/30 | 600â€“700 | card title |
| `type.body.lg` | 16/28 | 400â€“500 | important body |
| `type.body` | 14/24 | 400â€“500 | default UI |
| `type.body.sm` | 13/21 | 400â€“500 | dense UI |
| `type.label` | 12/20 | 500â€“600 | labels / tabs |
| `type.meta` | 11/18 | 400â€“500 | metadata |
| `type.metric.lg` | 28/36 | 700â€“800 | major KPI |
| `type.metric` | 20/30 | 700 | card KPI |

**Rules:** max 3 type levels per card; avoid oversized titles on operational screens; metrics use tabular numerals where supported.

## 3.3 Spacing
Base grid = **4px**. Canonical scale: `4, 8, 12, 16, 20, 24, 32, 40, 48, 64`.

Operational default:
- card inner gap: 12â€“16
- section gap: 20â€“24
- screen side padding mobile: 16
- tablet: 24
- desktop: 32
- dense row vertical padding: 10â€“12

## 3.4 Radius
`r6 / r10 / r14 / r18 / r22 / r28 / pill`.

Defaults:
- inputs/buttons: 12â€“14
- compact cards: 14â€“16
- main cards: 18
- sheets/dialogs: 22â€“28
- chips: pill

## 3.5 Elevation / Effects
| Level | Rule |
|---|---|
| `e0` | no shadow, subtle border |
| `e1` | 0 4 14 rgba(0,0,0,.18) |
| `e2` | 0 10 28 rgba(0,0,0,.26) |
| `e3` | 0 16 44 rgba(0,0,0,.32) |
| `glass` | backdrop blur 10â€“14px, translucent surface, subtle border |
| `gold-focus` | 0 0 0 1px rgba(217,151,18,.5), 0 0 20 rgba(217,151,18,.12) |

**Rule:** Max one glow emphasis inside a local visual group.

## 3.6 Iconography
- Lucide-compatible outline geometry
- 1.7â€“2.0 stroke weight
- sizes: 16 / 18 / 20 / 24
- 44x44 minimum interactive hit target
- status icon may use semantic color; default icons use text secondary

---

# 4) Layout System

## 4.1 Breakpoints
- Compact mobile: 320â€“389
- Mobile: 390â€“767
- Tablet: 768â€“1199
- Desktop: 1200+

## 4.2 Mobile Shell
- top app bar: 56â€“64
- optional context/search bar: 44â€“48
- bottom nav: 64â€“72 + safe-area
- content side padding: 16
- sticky action zone allowed when task critical
- body never horizontally scrolls

## 4.3 Tablet/Desktop
Same information architecture; do not invent separate product. Bottom navigation may adapt to rail/compact persistent navigation only when responsive breakpoint requires it, while maintaining destination parity.

## 4.4 Density Modes
- `comfortable`: forms, auth, onboarding
- `standard`: general app
- `dense`: tables, route lists, inventory, reports
No component may use arbitrary density outside these modes.

---

# 5) State System

## Global States
`default / hover / pressed / focus-visible / selected / disabled / read-only / loading / empty / error / offline / syncing / stale / success / warning / critical`

## Business/Semantic States
`available / reserved / low-stock / out-of-stock / blocked / pending-approval / approved / rejected / overdue / risk / opportunity / draft / submitted / completed / cancelled`

Every interactive/data component must declare supported states. No state may be represented by color alone.

---

# 6) Canonical Component Registry

Every UI object must map to one of these IDs or be added through versioned registry update.

## A. Shell & Navigation
- `DSO-NAV-001` AppShell
- `DSO-NAV-002` TopBar
- `DSO-NAV-003` Context/SearchBar
- `DSO-NAV-004` BottomNavigation
- `DSO-NAV-005` BottomNavItem
- `DSO-NAV-006` AIPrimaryNavAction
- `DSO-NAV-007` Breadcrumb/BackAction
- `DSO-NAV-008` SectionTabs
- `DSO-NAV-009` SegmentedControl
- `DSO-NAV-010` Pagination
- `DSO-NAV-011` Stepper
- `DSO-NAV-012` MoreMenu

## B. Actions
- `DSO-ACT-001` Button/Primary
- `DSO-ACT-002` Button/Secondary
- `DSO-ACT-003` Button/Tertiary
- `DSO-ACT-004` Button/Ghost
- `DSO-ACT-005` Button/Danger
- `DSO-ACT-006` IconButton
- `DSO-ACT-007` FloatingAction
- `DSO-ACT-008` SplitAction
- `DSO-ACT-009` InlineAction
- `DSO-ACT-010` StickyPrimaryAction

Sizes: S=36, M=44, L=52. Primary operational default=M. Mobile primary CTA can be L/full-width.

## C. Inputs & Forms
- `DSO-INP-001` TextField
- `DSO-INP-002` PasswordField
- `DSO-INP-003` SearchField
- `DSO-INP-004` NumberField
- `DSO-INP-005` CurrencyField
- `DSO-INP-006` TextArea
- `DSO-INP-007` Select
- `DSO-INP-008` MultiSelect
- `DSO-INP-009` Combobox
- `DSO-INP-010` Checkbox
- `DSO-INP-011` Radio
- `DSO-INP-012` Switch
- `DSO-INP-013` DatePicker
- `DSO-INP-014` TimePicker
- `DSO-INP-015` Range/Slider
- `DSO-INP-016` QuantityStepper
- `DSO-INP-017` FileUpload
- `DSO-INP-018` VoiceInput
- `DSO-INP-019` LocationInput
- `DSO-INP-020` FormField/Label/Error anatomy

Default field height: 48; dense 40â€“44; auth/primary form 52.

## D. Data Display
- `DSO-DAT-001` Card/Base
- `DSO-DAT-002` MetricCard
- `DSO-DAT-003` StatTile
- `DSO-DAT-004` SummaryStrip
- `DSO-DAT-005` List
- `DSO-DAT-006` ListRow
- `DSO-DAT-007` Avatar
- `DSO-DAT-008` EntityHeader
- `DSO-DAT-009` KeyValueRow
- `DSO-DAT-010` Badge
- `DSO-DAT-011` StatusChip
- `DSO-DAT-012` Tag
- `DSO-DAT-013` ProgressBar
- `DSO-DAT-014` ProgressRing
- `DSO-DAT-015` Timeline
- `DSO-DAT-016` ActivityItem
- `DSO-DAT-017` Accordion
- `DSO-DAT-018` DataTable
- `DSO-DAT-019` DataGrid
- `DSO-DAT-020` ColumnHeader

## E. Feedback / System
- `DSO-FBK-001` Toast
- `DSO-FBK-002` InlineAlert
- `DSO-FBK-003` Banner
- `DSO-FBK-004` LoadingSkeleton
- `DSO-FBK-005` Spinner
- `DSO-FBK-006` EmptyState
- `DSO-FBK-007` ErrorState
- `DSO-FBK-008` OfflineState
- `DSO-FBK-009` SyncIndicator
- `DSO-FBK-010` UpdateAvailable
- `DSO-FBK-011` ConfirmationState
- `DSO-FBK-012` PermissionDenied

## F. Overlays
- `DSO-OVR-001` Dialog
- `DSO-OVR-002` AlertDialog
- `DSO-OVR-003` BottomSheet
- `DSO-OVR-004` Drawer
- `DSO-OVR-005` Popover
- `DSO-OVR-006` Tooltip
- `DSO-OVR-007` ActionMenu
- `DSO-OVR-008` FullscreenTask

## G. AI
- `DSO-AI-001` AIComposer
- `DSO-AI-002` AIMessage/User
- `DSO-AI-003` AIMessage/Assistant
- `DSO-AI-004` AIActionCard
- `DSO-AI-005` AISuggestionChip
- `DSO-AI-006` AIInsightCard
- `DSO-AI-007` AIConfidence/Source
- `DSO-AI-008` AIThinkingState
- `DSO-AI-009` AIStreamingState
- `DSO-AI-010` AIMultimodalAttachment

## H. Customer / CRM
- `DSO-CRM-001` CustomerCard
- `DSO-CRM-002` Customer360Header
- `DSO-CRM-003` CustomerRiskBadge
- `DSO-CRM-004` CustomerBalanceSummary
- `DSO-CRM-005` CustomerContactActions
- `DSO-CRM-006` CustomerVisitHistory
- `DSO-CRM-007` CustomerOpportunity
- `DSO-CRM-008` CustomerRecommendation
- `DSO-CRM-009` CustomerFinancialSnapshot

## I. Route / Field Sales / Maps
- `DSO-RTE-001` RouteCard
- `DSO-RTE-002` RouteProgress
- `DSO-RTE-003` VisitCard
- `DSO-RTE-004` VisitStatus
- `DSO-RTE-005` MapCanvas
- `DSO-RTE-006` MapMarker/Customer
- `DSO-RTE-007` MapMarker/Opportunity
- `DSO-RTE-008` RouteLine
- `DSO-RTE-009` DistanceTimeChip
- `DSO-RTE-010` StartVisitAction
- `DSO-RTE-011` VisitCompletionSummary

## J. Catalog / Commerce / Orders
- `DSO-COM-001` ProductCard
- `DSO-COM-002` ProductListRow
- `DSO-COM-003` ProductImage
- `DSO-COM-004` PriceBlock
- `DSO-COM-005` StockAvailability
- `DSO-COM-006` PromotionBadge
- `DSO-COM-007` QuantityControl
- `DSO-COM-008` CartLine
- `DSO-COM-009` CartSummary
- `DSO-COM-010` OrderStatus
- `DSO-COM-011` CommercialPreview
- `DSO-COM-012` DiscountSummary
- `DSO-COM-013` GiftSummary
- `DSO-COM-014` CreditCheckSummary
- `DSO-COM-015` SubmitOrderAction
- `DSO-COM-016` DraftIndicator

## K. Inventory / Warehouse
- `DSO-INV-001` WarehouseSelector
- `DSO-INV-002` StockMetric
- `DSO-INV-003` StockRow
- `DSO-INV-004` ReservedStockIndicator
- `DSO-INV-005` LowStockAlert
- `DSO-INV-006` ReorderSuggestion
- `DSO-INV-007` WarehouseTransferStatus
- `DSO-INV-008` InventoryTrend
- `DSO-INV-009` SKUAvailabilityMatrix

## L. Finance / Treasury
- `DSO-FIN-001` MoneyMetric
- `DSO-FIN-002` BalanceCard
- `DSO-FIN-003` ReceivableRow
- `DSO-FIN-004` ChequeStatus
- `DSO-FIN-005` AgingBucket
- `DSO-FIN-006` CreditRiskIndicator
- `DSO-FIN-007` InvoiceSummary
- `DSO-FIN-008` PaymentStatus

## M. Reports / Analytics
- `DSO-RPT-001` KPIBlock
- `DSO-RPT-002` TrendChart
- `DSO-RPT-003` BarChart
- `DSO-RPT-004` DonutChart
- `DSO-RPT-005` Sparkline
- `DSO-RPT-006` RankingRow
- `DSO-RPT-007` ComparisonCard
- `DSO-RPT-008` FilterBar
- `DSO-RPT-009` DateRangeFilter
- `DSO-RPT-010` DrilldownAction
- `DSO-RPT-011` SemanticStateBadge

## N. Identity / Auth
- `DSO-AUTH-001` BrandLockup
- `DSO-AUTH-002` LoginPanel
- `DSO-AUTH-003` CredentialFieldGroup
- `DSO-AUTH-004` RememberCredential
- `DSO-AUTH-005` PasswordVisibility
- `DSO-AUTH-006` AuthError
- `DSO-AUTH-007` SessionChecking
- `DSO-AUTH-008` ProfileMenu

## O. Notifications / Attachments / Utility
- `DSO-UTL-001` NotificationItem
- `DSO-UTL-002` NotificationBadge
- `DSO-UTL-003` AttachmentTile
- `DSO-UTL-004` ImagePreview
- `DSO-UTL-005` DocumentPreview
- `DSO-UTL-006` VoiceClip
- `DSO-UTL-007` QR/BarcodeView
- `DSO-UTL-008` CopyableCode

---

# 7) Component Anatomy Rules

Every component definition must specify:
1. ID
2. Purpose
3. Anatomy
4. Token dependencies
5. Variants
6. States
7. Density
8. Responsive behavior
9. Accessibility behavior
10. RTL/LTR behavior
11. Figma counterpart
12. Frontend counterpart
13. Traceability ID
14. Evidence status

Mapping state must be one of:
- `Figma-only`
- `Code-only`
- `Mismatch`
- `Canonical Mapping Confirmed`

---

# 8) Pattern Registry

- `PAT-001` Search â†’ Filter â†’ Result List
- `PAT-002` Entity Summary â†’ Actions â†’ Detail Tabs
- `PAT-003` KPI Summary â†’ Trend â†’ Exceptions â†’ Drilldown
- `PAT-004` Route Overview â†’ Map â†’ Visit Queue â†’ Primary Action
- `PAT-005` Previsit Brief â†’ Risk â†’ Opportunity â†’ Recommended Action
- `PAT-006` Catalog â†’ Search/Filter â†’ Product â†’ Quantity â†’ Cart
- `PAT-007` Cart â†’ Commercial Preview â†’ Validation â†’ Submit
- `PAT-008` Operational Task â†’ Progress â†’ Exception â†’ Completion
- `PAT-009` AI Question â†’ Context â†’ Response â†’ Suggested Actions
- `PAT-010` Empty/Error/Offline â†’ Explanation â†’ Recovery Action
- `PAT-011` Dense Table â†’ Filter â†’ Sort â†’ Row Action â†’ Detail
- `PAT-012` Notification â†’ Severity â†’ Context â†’ Action

No screen may introduce a new repeated layout pattern without adding it here first.

---

# 9) Screen Archetypes

Visual references are grouped into these archetypes; a screen may combine at most two primary archetypes.

1. Hero / Immersive
2. Map / Intelligence
3. Progress / Journey
4. Ranking / Leaderboard
5. Challenge / Campaign
6. Learning / Mastery
7. Territory / Coverage
8. Inventory / Precision
9. Opportunity / Discovery
10. AI / Guidance
11. Dense Operational List
12. Analytical Dashboard
13. Transaction / Checkout
14. Entity 360

**Important:** archetype controls presentation, not content.

---

# 10) Responsive Rules

- 320px must remain usable without horizontal scroll.
- 390px is primary mobile design reference.
- Minimum touch target = 44x44.
- Primary mobile action = 48â€“52 high.
- Long Persian labels wrap intentionally; no clipped text.
- Desktop expansion must increase information efficiency, not merely stretch mobile cards.
- Tables collapse into responsive row/cards only when information hierarchy is preserved.
- Bottom sheets preferred to centered dialogs for task-heavy mobile flows.

---

# 11) Accessibility Rules

- WCAG AA target for text/controls.
- Focus-visible always present.
- Status not color-only.
- Motion respects `prefers-reduced-motion`.
- Inputs have persistent label; placeholder is not label.
- Icon-only actions require accessible name.
- Error message tied to field programmatically.
- Keyboard reachability on web/desktop.

---

# 12) Motion Rules

- Fast feedback: 100â€“140ms
- Standard transition: 160â€“220ms
- Overlay/sheet: 220â€“280ms
- Page/major transition: max 320ms
- easing: soft deceleration; no springy/game-like motion for enterprise flows
- glow/pulse only for AI listening, critical live state or deliberate attention cue

---

# 13) Login/Auth Visual Contract

The current functional Login is **not** visual source of truth.

Canonical login composition:
- restrained brand lockup, not oversized hero logo
- compact premium card/surface or integrated panel
- title hierarchy 26â€“32px, not poster scale
- fields 52px mobile, muted surface, subtle 1px border
- gold focus ring, not gold-filled input
- primary action uses muted gold gradient/solid with low glow
- one depth focal point only
- full mobile viewport fit with safe area and no horizontal overflow
- exact business/auth behavior remains from backend

---

# 14) Figma â†” Frontend Contract

Target chain:
`Figma Variables â†’ Semantic Tokens â†’ Component Variants â†’ Frontend Tokens â†’ React Components â†’ Visual Regression`

Naming:
- Figma: `NeginAI/<Family>/<Component>/<Variant>`
- React: `<Family><Component>` or domain component under feature
- CSS tokens: `--ng-*`
- Trace ID: `DSO-*`, `PAT-*`, `SCR-*`

No hardcoded color/radius/spacing in production component unless explicitly documented exception.

---

# 15) Definition of Done for Any UI Object

A component is `DONE` only when:
- visual definition exists
- all required states exist
- token binding exists
- responsive behavior defined
- RTL checked
- accessibility checked
- Figma mapping identified
- frontend mapping identified
- runtime evidence exists

No Evidence â†’ No COMPLETE.

---

# 16) Governance

New objects must follow:
`Need â†’ Check Registry â†’ Reuse/Variant if possible â†’ New Component only if structurally unique â†’ Token bind â†’ Figma â†’ Code mapping â†’ QA`

Version changes:
- patch: state/style correction without contract change
- minor: new component/pattern/token
- major: visual language or semantic component contract change

No existing canonical rule is immutable; changes require reconciliation and versioning.

---

# 17) Immediate Implementation Priority

**CURRENT**
1. Normalize tokens in code
2. Complete core component primitives
3. Replace ad-hoc Login visuals with canonical Auth components
4. Stabilize Shared Shell
5. Seller workflow components

**NEXT**
Customer360 â†’ Previsit â†’ Catalog/Order â†’ Reports â†’ Inventory â†’ AI â†’ System states

**FINAL**
Figma â†” React mapping â†’ responsive/accessibility regression â†’ visual quality gate 90+.


## Canonical Product Naming
- Official product name: `NeginAI`
- Always render the product name in Latin script exactly as `NeginAI`.
- Do not localize/transliterate it to Persian and do not write `Negin AI`, `Negin Ai`, or other variants.
- Surrounding UI copy may be Persian/RTL, but the brand token itself remains `NeginAI` with isolated LTR direction where needed.
