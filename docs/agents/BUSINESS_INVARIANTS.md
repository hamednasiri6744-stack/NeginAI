# NeginAI Business Invariants

These are engineering guardrails, not invented ERP specifications. Where an exact Varanegar/NGT rule is unknown,
the agent must discover or ask rather than fabricate it.

## 1. Route sales / visit lifecycle

- A visit/customer-call must remain traceable to the relevant actor, customer, route/tour and business date.
- Draft, submitted, accepted, failed and reconciled states must not be conflated.
- Retry must not create duplicate commercial actions.
- Offline/reconnect flows must preserve enough identity to reconcile the final server/ERP result.
- GPS/location rules are policy-driven; do not hard-code a new business threshold without a verified source.

## 2. Order lifecycle

- Local order intent and server/ERP acknowledgement are distinct states.
- Idempotency is required around submission/retry.
- A failed or ambiguous response must not be silently treated as accepted.
- Crosswalk identifiers between local request, NGT/API receipt and Varanegar/ERP record must remain auditable.
- Split/merge behavior, supplier allocation and approval semantics must follow verified contracts.

## 3. Quantity and units

- Base unit, sale unit, pack/carton conversion and display unit must not be interchanged implicitly.
- Conversion factors require a verified source.
- Rounding must be deterministic and tested where quantities or money are affected.

## 4. Pricing

- Price class/customer-specific price, effective date and applicable unit are part of pricing semantics.
- Do not silently replace verified pricing with a fallback when the fallback changes commercial meaning.
- Price calculations must preserve decimal precision and agreed rounding.
- Any precedence between list price, customer price, campaign price and overrides must come from verified evidence.

## 5. Discounts, offers and prizes

- Eligibility, thresholds, stacking/exclusivity, caps and effective periods are business rules, not UI decoration.
- Discount/prize evaluation must be deterministic for the same basket and policy snapshot.
- Do not change calculation order or stacking behavior without a test that captures the intended rule.
- Returned/cancelled quantities must not receive unintended benefits.

## 6. Tax and invoice totals

- Taxability, tax base, rounding and ordering relative to discounts must follow verified rules.
- Display totals and persisted/submitted totals must reconcile.
- Never hide a material rounding delta by formatting alone.

## 7. Credit and approvals

- Credit limit, outstanding balance, overdue policy and approval gates must not be bypassed by client-only logic.
- Unknown/failed credit checks must not be interpreted as approved unless the verified contract explicitly says so.
- Overrides require explicit authority/audit semantics.

## 8. Inventory / warehouse

- Available, on-hand, reserved, allocated, in-transit and sellable stock are distinct concepts.
- A UI stock number must state which concept it represents.
- Do not create production stock mutations through direct SQL.
- Reservation/release must be idempotent if/when implemented.

## 9. Distribution and logistics

- Planned route, actual visit sequence, shipment/delivery status and proof-of-delivery are separate states.
- Delivery exceptions must retain reason/status history.
- Route optimization must respect verified operational constraints (vehicle, capacity, time window, territory,
  customer priority, driver/seller assignment) rather than distance alone.
- Replanning must not erase the original plan needed for audit/comparison.

## 10. Data and analytics

- KPI definitions require explicit numerator, denominator, time grain, filters, exclusions and source.
- Production SQL is read-only by default and must not become the compute engine for heavy analytics.
- Source freshness and scope must be known before operational conclusions are presented as final.
- Semantic definitions should be reusable rather than duplicated ad hoc in UI/report queries.

## 11. Security and audit

- Secrets, credentials, private keys and runtime databases never belong in Git.
- Financial/commercial state changes require actor/time/result traceability.
- Error logs must not leak credentials or unnecessary personal data.

## Change rule

If a commit changes any invariant above, it must do at least one of:

- preserve the invariant and add/retain evidence;
- intentionally revise the invariant with user/business-owner approval and update this document/tests;
- remain blocked/open because the exact business rule is not yet verified.
