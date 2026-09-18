# NeginAI Product Architecture v1

Status: CANONICAL  
Approved principles: 2026-09-18

This document is the canonical product-level map. Detailed ownership and projection rules are enforced by:

- `docs/architecture/NEGINAI_ARCHITECTURE_CONTRACT_V1.md`
- `docs/architecture/NEGINAI_CANONICAL_CAPABILITY_REGISTRY_V1.csv`
- `scripts/architecture/validate_capability_registry.py`

## Product stack

`Sources -> Semantic Contracts -> Backend Read Models / Workflows -> Context Fusion -> AI Intelligence -> Product Surfaces`

### Sources
- Varanegar ERP: commercial/accounting truth.
- NGT: field-sales operational context.
- Cloud / grs: field telemetry and activity.
- Neshan: map/navigation service.
- NeginAI Backend: orchestration, workflow state, semantic composition, alerts, AI, controlled bridges.

## Seller navigation

1. **Today / Mission Control**
   - decision and action surface.
   - consumes shallow projections from owned domains.
   - never duplicates full workflows.

2. **Route / Field Execution**
   - route, map, stop sequence, visit execution, location/telemetry context.

3. **Order / Selling Workspace**
   - catalog, product, quantity, stock/price context, order/payment policy, preview, draft/saved request/final state.

4. **Customers / Customer Intelligence**
   - customer discovery, segmentation, Customer360.
   - finance/distribution/history appear as contextual depth while retaining their domain owner.

5. **Reports / Analysis**
   - analytical questions, trends, comparisons, aggregates, historical drilldown.

## Global surfaces

- **Alert Center** — cross-domain event/change lifecycle.
- **Negin AI** — ambient AI, contextual copilot, Next Best Action, agent actions, deep AI Workspace.
- **Profile / Settings** — identity, session, permissions, real settings/sync state.

## Contextual workspaces

These are not extra bottom-navigation modules:
- Visit Workspace
- Finance / Collections detail
- Distribution / Returns detail
- Product detail
- Official commercial preview
- Saved request / submission result

## Capability owner domains

- Identity & System
- Field Operations
- Customer Intelligence
- Commercial & Orders
- Finance & Collections
- Distribution & Returns
- Intelligence & Analysis
- AI Intelligence

Bounded enterprise/platform domains:
- Admin & Planning
- Warehouse Operations
- Platform & Knowledge

## Duplication rule

A business capability has one canonical owner.

Other modules may render only an approved:
`signal | badge | summary | context | aggregate | deep-link | alert | history`

A shared UI component may be reused freely.
A full business workflow may not be implemented twice.

## Example: returned cheque

Canonical owner:
**Finance & Collections**

Canonical detail:
**Finance contextual workspace / Customer360 > Finance > Cheques when customer-scoped**

Allowed projections:
- Today -> alert
- Customer360 -> badge/status
- Reports -> aggregate
- Alert Center -> alert
- Orders -> blocking/context signal

None of these projections owns returned-cheque semantics or recreates the full workflow.

## AI rule

AI is present across all product surfaces, but is not the source of ERP truth.

`Domain owns truth -> AI explains / predicts / prioritizes -> canonical capability executes`

AI actions must call the canonical capability boundary and inherit its permissions, confirmation rules, and write safety.

## Enterprise preservation

All existing backend/ERP capabilities remain inventoried even when they do not belong in Visitor navigation.

Warehouse operations remain a separate role-bounded workspace.
Admin/planning/control remain separate role-bounded workspaces.
Platform/knowledge APIs remain infrastructure capabilities.

Preservation does not mean exposing every capability on every screen.

## Implementation gate

Before adding or moving a feature:
1. locate its capability ID in the registry,
2. confirm its owner domain,
3. confirm canonical surface,
4. confirm source/semantic authority,
5. confirm current availability,
6. use only an allowed projection outside its canonical surface.

If no capability entry exists, architecture registration happens before UI implementation.
