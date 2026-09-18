# NeginAI Product Experience Contract v1.0

## Product philosophy
NeginAI is not a dashboard collection. It is a living, depth-first operational system that uses real NGT, Varanegar and NeginAI backend data to guide the user toward better commercial decisions.

Every user-facing module MUST satisfy four product questions:
1. LIVE — Does the UI visibly reflect state, change, loading, success, risk and opportunity?
2. DEPTH — Is Level 0 decision-oriented and compact, with detail revealed through meaningful depth rather than long scroll?
3. ACTION — Does every primary surface either inform a decision, trigger an action, or open a meaningful lower layer?
4. COMMERCIAL PRESSURE — Does real data create appropriate motivation or urgency toward better sales execution without fake gamification or invented KPIs?

## Canonical interaction model
- Level 0: one viewport when practical. Category, state, priority and next action only.
- Level 1: workspace for the selected domain/category.
- Level 2: focused detail / decision context.
- Route changes are reserved for true module transitions. In-module drill-down should prefer layered surfaces.
- Scroll is allowed only where the information type is inherently sequential or analytical (long lists, catalogs, timelines, detailed reports).
- Empty space must communicate depth or focus; it must not be accidental dead space.

## Living UI
Motion is semantic, not decorative.
- State change -> transition.
- New/changed data -> restrained reaction.
- Risk/urgent -> attention cue.
- Opportunity -> positive energy cue.
- Touch -> tactile press feedback.
- Loading -> skeleton/live state, not frozen empty surfaces.
Respect reduced motion and mobile GPU constraints.

## Motivation and urgency
Motivation and urgency MUST come from real operational data, not motivational copy.
Good signals include:
- target pace / validated performance delta,
- real sales opportunity,
- inactive/high-potential customer,
- stock and active promotion availability,
- price/promotion/reward changes,
- financial risk,
- route/visit opportunity,
- missed/follow-up actions,
- distribution state,
- operational alerts.

Never publish a KPI as official until its semantic contract is validated.

## Visual system
Canonical visual language: NeginAI Design System v2.
- Material DNA: Customer Workspace.
- Interaction DNA: Orders + Living UI.
- Information architecture: Depth-first.
- Navigation DNA: current Header + Bottom Nav.
All surfaces MUST use shared tokens/primitives for material, typography, radius, borders, depth and motion.

## Module intent
### Home
Sales momentum + risk + urgency + next best action. Not a route dashboard.

### Customers
Decision workspace: who should I sell to / follow up / protect? Customer list is a lower layer, not the product definition.

### Route
Operational execution: what should I do next, where, and why? Route state owns route detail.

### Customer 360
Understanding + decision: commercial history, financial risk, opportunity, visit/order actions.

### Orders
Fast selling workspace: product discovery, opportunity, quantity, official preview, credit/reward restrictions and completion.

### Reports
Analysis and discovery. Level 0 starts with analytical questions/domains; detailed analytical surfaces may scroll.

### Notifications
Operational Alert Center. Severity, acknowledgment and action path must be explicit.

## Anti-patterns
- Dashboard grid used only because data exists.
- Dead cards with no action/depth.
- Fake controls with no backend capability.
- Long Level-0 pages.
- Decorative motion unrelated to state.
- Tiny typography used to fit more cards.
- Duplicating module detail on Home.
- Fake motivation or unvalidated KPI scoring.
