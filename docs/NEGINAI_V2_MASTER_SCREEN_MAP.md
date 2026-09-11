# NeginAI v2 — Master Screen Map

Status: DESIGN PLANNING BASELINE
Date: 2026-09-11
Scope: UI/UX redesign only. Existing backend and business logic must be preserved.
Design baseline: Design System v2

Legend: R = existing surface to redesign; S = shared/system surface; N = planned design unit derived from an existing flow.

## A. Platform / Shell — 10
AUTH-01 | Login | R
PLT-01 | Home / AI Chat | R
PLT-02 | Conversations / History | R
PLT-03 | New Chat | R
PLT-04 | Notifications | R
PLT-05 | Automation Center | R
PLT-06 | Account / Profile | R
PLT-07 | Account Security | R
PLT-08 | Attachment / Excel Preview | R
PLT-09 | Install / PWA | R

## B. Seller / Field Sales — 24
SEL-01 | My Routes | R
SEL-02 | Day Route | R
SEL-03 | Route Customer List | R
MAP-01 | Route Map / Live Navigation | R
MAP-02 | Route Summary / Navigation Steps | R
CUS-01 | Customer 360 | R
CUS-02 | Customer Edit Draft / Location Capture | R
VIS-01 | Visit Workspace — Profile | R
VIS-02 | Visit Workspace — Order | R
VIS-03 | Saved Requests | R
VIS-04 | Visit Outcome / No-order | R
ORD-01 | Product Catalog | R
ORD-02 | Grouped Catalog | R
ORD-03 | Product Quick Detail | N
ORD-04 | Cart / Order Draft | R
ORD-05 | Order Preview / Review | R
ORD-06 | Order Complete / Result | R
FIN-01 | Open Invoices | R
FIN-02 | Open Invoice Detail | R
FIN-03 | Distribution In Progress | R
FIN-04 | Returned Cheques | R
RET-01 | Voucher / Return Report | R
BRD-01 | My Brands | R
REC-01 | Sales Recommendations | R

## C. Management / Admin — 8
ADM-01 | Control Overview | R
ADM-02 | Personnel Directory | R
ADM-03 | Personnel View Manager | R
ADM-04 | Branch Personnel | R
ADM-05 | Positions | R
ADM-06 | Position Editor | R
ADM-07 | Permissions Matrix | R
ORG-01 | Organization Structure / Proposals | R

## D. Planning — 5
PLN-01 | Planning Dashboard / Scenario List | R
PLN-02 | Scenario Create / Edit | R
PLN-03 | Scenario Detail / Values | R
PLN-04 | Assumptions / Audit | R
PLN-05 | Scenario Comparison | R

## E. Warehouse — 5
WHS-01 | Warehouse Overview | R
WHS-02 | Varanegar Sync / Snapshot Import | R
WHS-03 | Order Suggestions | R
WHS-04 | Prepared Supplier Orders | R
WHS-05 | Warehouse Access Gate | R

## F. Data / Admin Tools — 8
DAT-01 | Data Dashboard | R
DAT-02 | Schema Catalog | R
DAT-03 | Schema Object Detail | R
DAT-04 | Definitions | R
DAT-05 | Definition Editor | R
DAT-06 | SQL Workspace | R
DAT-07 | Query History | R
DAT-08 | Settings | R

## G. Native Android Seller Navigator — 6
AND-01 | Android Login | R
AND-02 | Route Selection | R
AND-03 | Route Mode Selection | R
AND-04 | Turn-by-turn Navigation | R
AND-05 | Off-route / Reroute | R
AND-06 | Android Install / Update | R

## H. Shared States — 12
SYS-01 | Loading / Skeleton | S
SYS-02 | Empty | S
SYS-03 | Error / Retry | S
SYS-04 | Offline | S
SYS-05 | Access Denied | S
SYS-06 | Session Expired | S
SYS-07 | Confirmation | S
SYS-08 | Destructive Confirmation | S
SYS-09 | Success / Submitted | S
SYS-10 | Sync Conflict | S
SYS-11 | Location / GPS Permission | S
SYS-12 | Device Permission State | S

## Totals
Main screen/design units: 66
Shared system states: 12
Master design units: 78

## Design waves
Wave 1: AUTH-01, PLT-01, SEL-01, SEL-02, SEL-03, MAP-01, CUS-01, VIS-01, ORD-01, ORD-04.
Wave 2: MAP-02, CUS-02, VIS-02..04, ORD-02..06, FIN-01..04, RET-01, BRD-01, REC-01.
Wave 3: ADM-01..07, ORG-01.
Wave 4: PLN-01..05.
Wave 5: WHS-01..05.
Wave 6: DAT-01..08.
Wave 7: AND-01..06.
Shared states SYS-01..12 are designed once and reused across all waves.

## Release rule
No screen is done until it has mobile 390, tablet 768, desktop 1440 where applicable, RTL, loading/empty/error states, component mapping, responsive behavior, and feature-parity verification against the current implementation.

## Wave 1 detailed execution order
01 AUTH-01 — establish entry, branding, form controls and responsive shell.
02 PLT-01 — establish app chrome, primary navigation, AI workspace and home cards.
03 SEL-01 — establish route cards, filters, summary metrics and seller context.
04 SEL-02 — establish day-plan hierarchy, progress and primary actions.
05 SEL-03 — establish customer list density, status chips, search and sorting.
06 MAP-01 — establish map chrome, live navigation cards, route progress and bottom actions.
07 CUS-01 — establish Customer 360 information hierarchy, financial summary and next actions.
08 VIS-01 — establish visit workflow, customer context and visit progress.
09 ORD-01 — establish product discovery, filters, stock, price and quantity patterns.
10 ORD-04 — establish cart, totals, promotions and final order actions.

Wave 1 dependency chain: AUTH-01 -> PLT-01 -> SEL-01 -> SEL-02 -> SEL-03 -> MAP-01 -> CUS-01 -> VIS-01 -> ORD-01 -> ORD-04.

Design rule: no later wave begins before this chain is visually accepted as one coherent product journey.
