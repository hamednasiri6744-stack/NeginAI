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
| Customer profile | `/seller-workspace/routes/{path_id}/customers/{customer_id}/profile` | GET | NEXT |
| Visit workspace | `/seller-workspace/routes/{path_id}/customers/{customer_id}/visit-workspace` | GET | NEXT |
| Visit policy | `/seller-workspace/previsit/policy?path_id=...&customer_id=...` | GET | NEXT |
| Start visit | `/seller-workspace/previsit/visits` | POST | NEXT |
| Previsit context/catalog | `/seller-workspace/previsit/context` | GET | NEXT |
| Preview | `/seller-workspace/previsit/preview` | POST | NEXT |
| Draft | `/seller-workspace/previsit/visits/{visit_id}/draft` | PUT | NEXT |
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