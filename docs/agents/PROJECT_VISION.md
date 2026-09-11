# NeginAI Project Vision Contract

## Purpose

NeginAI is the company-facing modernization layer around route sales, field execution and Varanegar/NGT-backed
business workflows. Engineering decisions must move the product toward a reliable, production-grade assistant and
operational platform rather than a disconnected collection of demos.

## Primary product outcomes

1. Give field sellers/visitors, supervisors and managers a faster and safer workflow than the legacy experience.
2. Preserve verified Varanegar/NGT business semantics while improving usability, automation and decision support.
3. Keep mobile/PWA/Android behavior coherent with backend contracts and offline/retry requirements.
4. Make operational data useful for reporting, alerts, KPI monitoring and future enterprise intelligence.
5. Reduce manual work without creating silent financial, inventory, pricing, tax or reconciliation errors.

## Engineering principles

- Business correctness before visual convenience.
- Explicit contracts before reverse-engineered guesses.
- Idempotent/retriable integration before "happy path only" delivery.
- Read-only production SQL by default; approved application/API boundaries own writes.
- Minimal load on production systems; analytical workloads belong on local/analytics planes.
- Reversible, testable changes over broad rewrites.
- One source of truth per business concept where possible.
- Auditability for state transitions and financially meaningful actions.
- Mobile-first usability for field execution.
- Backward compatibility when changing an existing production-facing contract.
- No secrets or runtime state in source control.
- No writes to the boss/reference workspace.

## Current architectural direction

The active local writable repository is `D:\Projects\NeginAI`.
The reference/boss workspace is read-only.

Core implementation areas currently include:

- FastAPI/Python backend under `app/`
- web/PWA shell and seller experience under `app/static/`
- Android integration under `android/`
- local runtime state under `data/` (not source-controlled)
- NGT/Varanegar integration and reconciliation services
- tests under `tests/`
- project knowledge and handoff documents under `docs/` and `knowledge/`

## Commit-level vision test

Every material commit should be explainable with all four answers:

1. **Outcome** — which user/business outcome does this advance?
2. **Contract** — which API/data/business contract does it preserve or intentionally change?
3. **Evidence** — what test, trace, fixture, reproduction or observation verifies it?
4. **Risk** — what could break in sales, pricing, tax, inventory, visit, delivery or reconciliation behavior?

A commit that cannot answer these questions is not automatically wrong, but it requires explicit review before
being treated as production-ready.
