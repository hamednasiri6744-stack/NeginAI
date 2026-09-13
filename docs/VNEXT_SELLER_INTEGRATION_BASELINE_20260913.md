# NeginAI vNext — Seller Integration Baseline

Date: 2026-09-13
Scope: Frontend ↔ FastAPI contracts only. No Varanegar write activation.

## Binding rule

No endpoint, payload, field, data relation, auth assumption, or business rule may be invented in vNext.
Implementation may use only contracts confirmed from the current backend source/runtime. Unknown items stay `NEEDS_VALIDATION`.

## Confirmed architecture

`vNext React -> same-origin FastAPI -> existing Seller Workspace services -> Varanegar/NGT read contracts + NeginAI local state`

Varanegar write registration exists as a separate gated bridge and is intentionally deferred to the final project phase.

## Current contract matrix

| UI flow | Backend contract | Method | vNext status |
| --- | --- | --- | --- |
| Session check | `/auth/me` | GET | LIVE_INTEGRATED |
| Login | `/auth/login` | POST | LIVE_INTEGRATED |
| Logout | `/auth/logout` | POST | LIVE_INTEGRATED |
| Seller routes | `/seller-workspace/routes` | GET | LIVE_INTEGRATED |
| Route customers | `/seller-workspace/routes/{path_id}/customers` | GET | LIVE_INTEGRATED |
| Day route | route id from `/seller-workspace/routes`, customer state from route customers | GET | LIVE_INTEGRATED |
| Customer profile | `/seller-workspace/routes/{path_id}/customers/{customer_id}/profile` | GET | LIVE_INTEGRATED |
| Visit workspace | `/seller-workspace/routes/{path_id}/customers/{customer_id}/visit-workspace` | GET | LIVE_INTEGRATED |
| Visit policy | `/seller-workspace/previsit/policy?path_id=...&customer_id=...` | GET | LIVE_INTEGRATED |
| Start visit | `/seller-workspace/previsit/visits` | POST | LIVE_INTEGRATED |
| Previsit context/catalog | `/seller-workspace/previsit/context` | GET | LIVE_INTEGRATED |
| Preview | `/seller-workspace/previsit/preview` | POST | NEXT |
| Draft | `/seller-workspace/previsit/visits/{visit_id}/draft` | PUT | LIVE_INTEGRATED |
| Saved requests | `/seller-workspace/previsit/visits/{visit_id}/saved-requests` | GET/POST | NEXT |
| Complete visit | `/seller-workspace/previsit/visits/{visit_id}/complete` | POST | FINAL_PRE_WRITE |
| Neshan map config | `/seller-workspace/map-config` | GET | NEEDS_VALIDATION |
| Route map plan | `/seller-workspace/routes/{path_id}/map-plan` | GET | NEXT |
| Route map leg | `/seller-workspace/routes/{path_id}/map-leg` | GET | NEXT |
| Varanegar order registration | existing gated bridge | internal backend call | FINAL_PHASE_ONLY |

## Navigation contract

vNext passes existing backend identities via URL query parameters:

- `pathId`
- `customerId`

These values are identifiers only; no business data is encoded into navigation state.

## Deferred write boundary

The Varanegar order bridge stays disabled throughout UI/read integration and launch-parity work.
Write activation is the final phase after full contract parity, preview/validation, idempotency, transaction, numbering, permission, rollback, and production verification.

## Closure validation

- `npm run lint`: PASS
- `npm run build`: PASS
- `git diff --check`: PASS
- `tests/test_seller_workspace.py`: 37 passed

Known non-blocking pre-existing test warnings are explicitly deferred from this frontend integration slice:

- Pydantic warning for a `schema` field shadowing `BaseModel.schema`.
- `datetime.utcnow()` deprecation warning in `app/database.py`.
- Windows pytest temporary-directory cleanup permission warning after the test suite has already passed.

These warnings do not change Seller contract behavior and are not launch blockers for this slice; they should be handled in a dedicated backend/tooling maintenance change rather than mixed into the vNext Seller integration commit.
