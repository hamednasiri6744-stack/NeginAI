# NeginAI System Inventory — 2026-09-18

> Canonical discovery snapshot built from the live SQL Server, live FastAPI OpenAPI, backend source, frontend API consumption, and runtime listener state.
> This document is inventory, not product architecture. Architecture decisions should be made after this inventory is accepted.

## 1. Executive snapshot

- Live SQL Server: **ServerNew**
- Primary connected database: **NeginPakhsh**
- SQL access from NeginAI backend: **configured / live**
- Accessible business databases: **NeginPakhsh, VNDBBACK, Cloud, grs**
- NeginPakhsh live objects: **8,524**
- NGT schema in NeginPakhsh: **170 tables, 53 views, 67 procedures, 11 functions**
- Live backend OpenAPI: **252 endpoints**
- Seller Workspace endpoints: **31**
- Warehouse Assistant endpoints: **141**
- Frontend API paths currently consumed by vNext wrapper: **~33**
- Neshan Web API: **configured**
- Neshan Service API: **configured**
- Direct NGT REST API in current runtime: **not configured**
- NGT pilot send: **disabled**
- Varanegar final order bridge: **disabled**
- Varanegar final order commit: **disabled**
- Varanegar numbering verification: **not verified**
- Direct Varanegar order SQL bridge credentials: **not configured**
- Automation runtime: **disabled**
- Enterprise DB / Redis / command outbox: **not configured in current local runtime**

## 2. Live databases

### NeginPakhsh
Primary operational Varanegar / NGT database.

Important schemas:
- **dbo** — 1066 tables / 857 views / 2905 procedures / 199 functions
- **SLE** — sales/order/distribution: 172 tables / 100 views / 485 procedures / 55 functions
- **FRU** — reporting/operational models: 108 tables / 623 views
- **GNR** — master data: 195 tables / 142 views / 179 procedures / 57 functions
- **Acc** — receivables/finance: 54 tables / 62 views / 185 procedures / 18 functions
- **NGT** — mobile/visit/order context: 170 tables / 53 views / 67 procedures / 11 functions
- **inv** — stock/cardex/inventory: 32 tables / 40 views / 136 procedures / 6 functions
- **ICA** — supplier/purchase invoice domain: 44 tables / 68 views
- **GRS** — organizational/related operational data: 25 tables / 5 views
- **NeginAI** — controlled integration procedures: 12 tables / 5 procedures
- **rpt / BI / STAT** — reporting/analytical helpers

### VNDBBACK
Large read-oriented mirror/backup-style Varanegar dataset with 3,991 objects.
Contains the same major business schemas: SLE, FRU, GNR, Acc, NGT, inv, ICA, GRS, etc.
Useful for historical/accounting investigation, but should not become the primary live operational source without an explicit semantic contract.

### Cloud
85 objects, including:
- Companies / Branches / CompanyPersonnels
- CompanyPersonnelRoutes
- Customers / Products / Brands
- Device and company device status
- RegionAreas / RegionAreaPoints
- SmartRoutePoints
- PersonnelDailyActivityEvents
- PersonnelDailyActivityPoints and histories
- tracking/permissions/queue infrastructure

This is a strong candidate source for **field telemetry, GPS/activity history, route/region context, and device state**.

### grs
70 tables with a closely related field-activity model:
- CompanyPersonnels / CompanyPersonnelRoutes
- Customers / Products / Brands
- PersonnelDailyActivityEvents
- PersonnelDailyActivityPoints / histories
- RegionAreas / RegionAreaPoints
- TrackingProducts
- Devices, identities, permissions

This should be evaluated as a distinct source for **tracking and personnel field activity**, not treated as a generic HR database.

---

## 3. NGT capability inventory

NeginAI backend currently references at least 44 NGT objects directly.

### A. Seller identity / device policy
- NGT.Personnels
- NGT.Users
- NGT.DeviceUsers
- NGT.DeviceSettings
- NGT.AppSettings
- NGT.BaseValues
- NGT.PublicValues

Capabilities:
- resolve seller identity
- device/order policy
- GPS/distance controls
- customer edit permissions
- visit constraints
- allowed report/finance visibility

### B. Route / calendar / visit planning
- NGT.VisitTemplates
- NGT.VisitTemplatePaths
- NGT.VisitTemplatePathCustomers
- NGT.VisitTemplatePathSecondaryCustomers
- NGT.VisitPlans
- NGT.VisitPlanVacations
- NGT.DayPaths
- NGT.Tours
- NGT.CalendarTemplates
- NGT.CalendarTemplateHolidays

Capabilities:
- assigned routes
- today's effective route
- working/off days
- explicit day-path overrides
- existing tour detection
- route rotation
- route customer membership

### C. Customer master / segmentation
- NGT.Customers
- NGT.CustomerCategories
- NGT.CustomerLevels
- NGT.CustomerMainSubTypes
- NGT.CustomerOwnerTypes
- NGT.CustomerActivities
- NGT.NoSaleReasons

Capabilities:
- customer identity/profile
- segmentation/classification
- visit/outcome context
- no-sale reasons

### D. Catalog / product template
- NGT.ProductTemplates
- NGT.ProductTemplateDetails
- NGT.Catalogs
- NGT.CatalogProducts
- NGT.ProductUnits
- NGT.Units
- NGT.ImageInfoes

Capabilities:
- seller-specific sellable catalog
- permitted brands/products
- units
- product images/catalog structure

### E. Price / stock / commercial context
- NGT.ContractPrices
- NGT.Stocks

Capabilities:
- contract/base price context
- stock/warehouse context

Important: **official final commercial calculation is designed to come from NGT EVC Presale REST API**, not from local inference.

### F. Order/payment permissions
- NGT.DeviceOrderTypes
- NGT.OrderTypes
- NGT.PaymentTypes
- NGT.PaymentTypeOrders
- NGT.DealerPaymentTypes

Capabilities:
- seller permitted order types
- payment methods/usance
- payment/order compatibility

### G. Call/order operational history
- NGT.CustomerCalls
- NGT.CustomerCallOrders
- NGT.CustomerCallOrderLines

Potential:
- customer contact/order interaction history
- currently underused in the visitor UI

---

## 4. Varanegar / ERP domain inventory

### Sales and orders — SLE / dbo
Key referenced objects:
- SLE.OrdersReview
- SLE.tblOrderHdr / tblOrderItm
- SLE.tblSaleHdr / tblSaleItm
- SLE.tblSaleVocherHdr
- SLE.tblDist
- SLE.tblCPrice
- SLE.tblDiscount
- SLE.tblDiscountCondition
- SLE.tblDiscountGoods
- SLE.tblFreeInvoiceHdr / tblFreeInvoiceItm
- dbo.SalesReviewFast
- dbo.SalesReturnReviewFast

Capabilities:
- sales
- returns
- order conversion
- sales voucher
- distribution
- price contracts
- discount/rule context
- free/prize invoice context

### Customer / product master — GNR / FRU
Key objects:
- GNR.tblCust / GNR.vwCust
- GNR.tblGoods
- GNR.tblBrand
- GNR.tblManufacturer
- GNR.tblGoodsGroup
- GNR.tblGoodsMainSubType
- GNR.tblSupplier / tblGoodsSupplier
- GNR.tblStockDC / tblStockGoods
- GNR.vwPersonnel
- FRU.GoodsModel
- FRU.StockGoodsModel
- FRU.NGT_TourCustomerModel

Capabilities:
- customer master
- brand/manufacturer/group hierarchy
- goods master
- supplier
- stock/DC mapping
- personnel mapping
- reporting models

### Receivables / finance — Acc / dbo
Key objects:
- Acc.vwCustomerBalance
- Acc.vwRcvSaleReview
- Acc.vwRcvPaymentsReview
- Acc.vwRcvChequeReview
- Acc.vwRcvRetChequeReview
- dbo.vwReview_RcvAccountCardex2
- dbo.vwReview_RcvAccountSale2
- dbo.vwReview_RcvAccountSettlement2
- dbo.vwReview_TreasuryReceipt2
- dbo.SettlementFast
- dbo.InvoiceReceipt
- dbo.Receipt2
- dbo.RCheque2 / RChequeHistory

Capabilities:
- customer balance
- open invoice / settlement state
- receipts
- cheque status/history
- returned cheque
- customer cardex
- collection risk

### Inventory — inv / dbo
Key objects:
- inv.tblVocherHdr / inv.tblVocherItm
- inv.vwGoodsCardex
- inv.tblCardexType
- dbo.vwReview_StockProduct2
- dbo.vwReview_StockProductGroup2
- dbo.vwReview_StockCardex2

Capabilities:
- stock
- stock movement
- inventory voucher
- product/group inventory analysis

### Purchase / supplier — ICA
Key objects:
- ICA.TblSupInvoiceHdr
- ICA.TblSupInvoiceItm
- ICA.TblSupInvoiceItmXToll
- ICA.TblSupInvoiceTolls
- ICA.tblSupInvInvoiceRelation

Capabilities:
- confirmed purchase price
- supplier invoice
- latest-purchase-cost / profitability basis

### Controlled NeginAI procedures
- NeginAI.usp_SubmitValidatedOrder
- NeginAI.usp_CreateCheckbarReceipt
- NeginAI.usp_CreateCheckbarReceiptV2
- NeginAI.usp_CreateInterwarehouseCredit
- NeginAI.usp_CreatePurchaseInvoiceFromReceipt

These are controlled write bridges and must remain feature-flagged, transactional, auditable, and disabled by default until explicitly verified.

---

## 5. Verified Varanegar semantic routes already encoded in backend

The backend already contains a business ontology for:
- profit by last purchase price
- previsit / controlled order
- returned cheque
- invoice balance
- customer cardex
- settlement
- receipt/collection
- sales voucher
- customer order/request
- distribution
- inventory
- sales/returns

This is important: architecture should reuse this semantic layer rather than make the UI invent independent meanings for sales, balances, receipts, or vouchers.

---

## 6. Seller Workspace backend — 31 live endpoints

### Identity / route / customer
- GET /seller-workspace/routes
- GET /seller-workspace/routes/{path_id}/customers
- GET /seller-workspace/routes/{path_id}/customers/{customer_id}/profile
- GET /seller-workspace/customers/{customer_id}/profile
- PUT /seller-workspace/routes/{path_id}/customers/{customer_id}/profile-draft
- GET /seller-workspace/routes/{path_id}/customers/{customer_id}/visit-workspace

### Maps
- GET /seller-workspace/map-config
- GET /seller-workspace/routes/{path_id}/map-plan
- GET /seller-workspace/routes/{path_id}/map-leg

### Seller commercial/financial context
- GET /seller-workspace/brands
- GET /seller-workspace/open-invoices
- GET /seller-workspace/open-invoices/{customer_id}
- GET /seller-workspace/returned-cheques
- GET /seller-workspace/distribution-in-progress
- GET /seller-workspace/voucher-return-report
- GET /seller-workspace/target-pulse

### Previsit / order workflow
- GET /seller-workspace/previsit/context
- GET /seller-workspace/previsit/browse-context
- GET /seller-workspace/previsit/policy
- POST /seller-workspace/previsit/preview
- POST /seller-workspace/previsit/warmup
- GET /seller-workspace/previsit/catalog-images/{catalog_id}/{image_name}
- POST /seller-workspace/previsit/visits
- GET /seller-workspace/previsit/visits/{visit_id}
- PUT /seller-workspace/previsit/visits/{visit_id}/draft
- POST /seller-workspace/previsit/visits/{visit_id}/complete
- GET/POST /seller-workspace/previsit/visits/{visit_id}/saved-requests
- GET/PUT /seller-workspace/previsit/visits/{visit_id}/saved-requests/{request_id}
- GET /seller-workspace/routes/{path_id}/saved-requests

---

## 7. Current frontend consumption

vNext currently exposes/uses roughly 33 backend paths, mainly:
- auth
- notifications
- chat
- seller routes/customers/profile
- maps
- visit workflow
- previsit context/browse/preview
- saved requests
- open invoices
- returned cheques
- distribution
- voucher returns
- target pulse

### Seller Workspace endpoints with no direct frontend reference found
- /seller-workspace/brands
- /seller-workspace/open-invoices/{customer_id}
- /seller-workspace/previsit/catalog-images/{catalog_id}/{image_name}
- /seller-workspace/previsit/warmup

These should be reviewed before adding any new backend feature. At least some can materially improve UI:
- brands -> commercial opportunity / filters
- per-customer open invoices -> Customer360 financial layer
- catalog images -> Orders visual product layer
- warmup -> perceived order-screen performance

---

## 8. Previsit/order truth

### What is available now
- live route/customer/catalog context from SQL/NGT data
- allowed warehouses/order types/payment methods
- stock validation
- local visit and order draft workflow
- saved requests
- official preview endpoint exists in backend
- discount/prize/credit normalization exists
- alert observers exist for official quotes and credit blocks

### Critical current runtime limitation
The official NGT REST connection is **not configured** in this runtime.

Therefore:
- NGT EVC official preview cannot be considered operational until NGT_API_* settings are configured and verified.
- Discount, prize and official final price must not be claimed as officially calculated when EVC was not executed.

### Final Varanegar order submission
Current runtime:
- bridge disabled
- commit disabled
- numbering unverified
- bridge SQL credentials unconfigured

Therefore final Varanegar registration is currently **not an active capability**.
The product must clearly separate:
1. cart/draft
2. local saved request
3. official NGT preview
4. final Varanegar commit

---

## 9. Commercial alerts / urgency engine already present

Operational notification backend can observe:
- route assignment changes
- route customer changes
- returned cheque changes
- distribution changes
- voucher returns
- credit blocks
- official quote changes
- commercial policy changes

Commercial policy/alert sources include:
- price change
- discount rule change
- prize/reward change
- seller brand scope

This is the correct seed for a future Commercial Intelligence layer.

---

## 10. Targets / performance

Backend has seller_target_pulse.

Current semantic status is intentionally gated until KPI semantics are validated.
The UI must not treat an unvalidated target/sales aggregation as canonical.

Architecture implication:
- performance layer may show validated facts immediately
- target achievement appears only after semantic validation

---

## 11. Maps / tracking

### Neshan
Both Web and Service API keys are configured.
Backend exposes:
- map-config
- route map-plan
- route map-leg

### NGT
Provides route and customer membership plus location policy.

### Cloud / grs
Contain field telemetry and activity structures:
- PersonnelDailyActivityEvents
- PersonnelDailyActivityPoints
- histories
- CompanyPersonnelRoutes
- RegionAreas / RegionAreaPoints
- devices/status

Major opportunity:
**Route Execution / Field Activity** can eventually combine NGT plan + Neshan navigation + Cloud/grs actual field telemetry.
This is currently underused.

---

## 12. Backend domains outside the visitor UI

Live OpenAPI = 252 endpoints.

Major domains:
- Warehouse Assistant — 141
- Seller Workspace — 31
- Chat/Assistant — 15+
- Supplier Portal — 9
- Automations — 8
- Planning — 8
- Schema — 8
- Authentication — 5
- Definitions — 5
- Control — 4
- Organization Structure — 4
- Push — 4
- Entities — 3
- Health — 3

Warehouse Assistant itself includes:
- checkbars
- interwarehouse transfers
- purchase contracts
- supplier portal
- automatic preorders
- supplier orders
- sale-price contracts
- inventory
- fulfillment
- purchase invoices
- supply scope
- automatic settings
- table layouts
- SMS settings
- snapshots/sync/suggestions
- unbilled receipts

This is a separate enterprise operations domain and should not be mixed into Visitor information architecture just because it shares one backend.

---

## 13. Runtime infrastructure snapshot

Currently listening:
- 4180 — Vite dev
- 4183 — Vite preview
- 5678 — n8n
- 8007 — NeginAI backend
- 8766 — MCP
- 8770 — Master agent
- 8775 — n8n MCP
- 8777 — Code-X
- 8781 — Data-X
- 8782 — Automation-X

Not listening in this snapshot:
- 8778 — UX-X
- 8791 — Unified Gateway
- 8080 — Airflow

Process state:
- Cloudflared: running
- Tailscale: running

Infra availability must not be conflated with app feature availability.

---

## 14. Source → Backend → UI capability matrix

| Capability | Primary source | Backend | vNext UI | State |
|---|---|---:|---:|---|
| Seller identity/org | GNR + NGT | Yes | Yes | Active |
| Working calendar | NGT | Yes | Yes | Active |
| Assigned routes | NGT | Yes | Yes | Active |
| Route customers | NGT | Yes | Yes | Active |
| Customer360 | NGT + GNR + Acc + SLE | Yes | Yes | Active / expandable |
| GPS/location policy | NGT | Yes | Partial | Underused |
| Actual field telemetry | Cloud/grs | Not in Seller Workspace | No | Major gap |
| Neshan map/navigation | Neshan + NGT | Yes | Yes | Active |
| Catalog | NGT product template | Yes | Yes | Active |
| Seller brands | NGT | Yes | No direct usage | Gap |
| Product images | NGT catalog image endpoint | Yes | No direct usage found | Gap |
| Stock | NGT/FRU/inv | Yes | Yes | Active |
| Contract/base price | NGT/SLE | Yes | Partial | Active |
| Official final price | NGT EVC REST | Backend code exists | Preview UI exists | Runtime blocked by config |
| Discount/prize rules | SLE + NGT EVC | Yes | Partial | Needs official EVC |
| Credit control | ERP/NGT | Yes | Preview/alerts | Needs official flow verification |
| Visit workflow | NGT policy + local state | Yes | Yes | Active |
| Draft/saved order requests | local NeginAI store | Yes | Yes | Active |
| Final Varanegar order | controlled bridge | Code exists | Should not claim final | Disabled |
| Open invoices | Acc | Yes | Yes | Active |
| Customer-specific open invoices | Acc | Yes | No direct usage found | Gap |
| Returned cheques | Acc | Yes | Yes | Active |
| Customer cardex | Acc/dbo | Semantic support | Partial | Gap/expand |
| Receipts/settlement | Acc/dbo | Semantic support | Limited | Gap |
| Distribution | SLE/dbo | Yes | Yes | Active |
| Voucher returns | SLE/dbo | Yes | Yes | Active |
| Target pulse | Planning + SLE | Yes | Gated | Semantic validation required |
| Operational alerts | multi-source + local store | Yes | Yes | Active |
| Automation | local + assistant | Yes | Minimal | Runtime disabled |
| Planning | local planning store | Yes | Visitor no | Admin domain |
| AI/chat | assistant backend | Yes | Yes | Runtime provider should be verified separately |
| Warehouse operations | ERP + warehouse store | Extensive | Visitor no | Separate product/domain |

---

## 15. Architectural conclusions from inventory — not yet the final architecture

1. **NGT is the operational field-sales context layer**, not the whole ERP.
2. **Varanegar SQL domains are the commercial truth layer** for sales, finance, inventory, orders, distribution and accounting semantics.
3. **Cloud/grs are valuable field telemetry sources** and should be evaluated for actual movement/activity, not duplicated into NGT concepts.
4. **NeginAI backend is already an orchestration/semantic layer**, not just an API proxy.
5. **Visitor vNext currently exposes only a fraction of backend capability.**
6. **Warehouse Assistant is a separate enterprise domain** and should remain bounded from Visitor UX.
7. Product architecture must distinguish:
   - source-of-truth data
   - semantic interpretation
   - operational workflow
   - controlled write bridges
   - intelligence/alerts
   - presentation
8. Do not add new frontend cards before deciding which domain owns the concept.
9. A bottom-nav module must represent a stable user job/domain. Lower-layer details must stay inside that domain instead of routing to another bottom-nav module.
10. Commercial Intelligence should be built above verified source data and semantic contracts, not by inventing scores in the UI.

## 16. Next architecture step

Build the product architecture from jobs-to-be-done and these data domains:
- Command / Momentum
- Customer Intelligence
- Route Execution
- Selling / Order Workspace
- Commercial Intelligence / Alert Center
- Analysis / Reports
- bounded Admin/Planning
- bounded Warehouse Operations

Do not implement this architecture until the inventory is reviewed and accepted.
