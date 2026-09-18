# NeginAI Performance Guardrails

Goal: adding features must not silently degrade startup, navigation, animation smoothness, or background network load.

Current measured production baseline (2026-09-19):
- Initial entry JS: ~351.9 KB raw
- Initial entry CSS: ~293.7 KB raw
- Initial HTML-linked assets: ~723.0 KB raw
- Largest current lazy Visitor feature chunk: ~42 KB raw
- Floating Negin AI chunk: ~10.4 KB raw

Enforced budgets:
- Initial entry JS <= 370 KB
- Initial entry CSS <= 305 KB
- Initial HTML-linked assets <= 740 KB
- Each lazy Visitor/feature JS chunk <= 70 KB

`npm run build` now runs the performance budget check after the production build. A regression fails the build.

Architecture rules:
- New substantial screens/features are lazy-loaded by default.
- Heavy optional features must not enter the initial app shell.
- Do not add page-specific CSS to global.css; keep new styling route/component-scoped.
- Infinite motion, blur, refraction, and decorative animation must stop when hidden or disabled.
- Style Lab dynamic motion is test-only and runs only while Style Lab is explicitly enabled.
- Prefer one live channel over duplicate polling; fallback polling is allowed only when the live channel is unavailable.
- Preserve server-state caching and avoid duplicate requests for the same resource.
- Lists/maps with large datasets must use incremental/virtual rendering where practical.
- Large new dependencies require bundle-size review before merge.
- Do not increase a performance budget merely to make a build pass; split, defer, or optimize the feature first.

Next optimization target:
- Split legacy global.css by route/component. It is currently the largest structural CSS cost and should be migrated incrementally and reversibly.
