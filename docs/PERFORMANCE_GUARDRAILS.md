# NeginAI Performance Guardrails

Goal: adding features must not silently degrade startup, navigation, animation smoothness, or background network load.

Current measured production baseline (2026-09-19):
- Initial entry JS: ~351.9 KB raw
- Initial entry CSS: ~222.1 KB raw
- Initial HTML-linked assets: ~651.3 KB raw
- Largest current lazy Visitor feature chunk: ~42 KB raw
- Floating Negin AI chunk: ~10.4 KB raw

Enforced budgets:
- Initial entry JS <= 370 KB
- Initial entry CSS <= 235 KB
- Initial HTML-linked assets <= 665 KB
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

Phase 2 runtime cleanup:
- Removed eager map-plan prefetch from app bootstrap; the route map requests its plan only when the Route module is opened.
- Removed unreachable legacy full-page Negin AI code and CSS after migration to the floating assistant.

Phase 3 assistant isolation:
- Floating assistant launcher remains lightweight and persistent.
- Chat panel JS/CSS is now downloaded only after the user opens Negin AI for the first time.
- While the assistant is closed before first use, it does not subscribe to Route/Customer/Workflow context updates.
- Conversation state is owned by the launcher, so close/open preserves the current conversation while the panel itself can unmount.

Route-scoped CSS phase 1:
- Moved final Customers workspace CSS into the lazy Customers route chunk.
- Moved final Reports analysis CSS into the lazy Reports route chunk.
- Moved Orders commercial-guidance CSS into the lazy Orders route chunk.
- Moved notification semantic-category CSS into the lazy Notifications route chunk.
- Initial CSS dropped from ~285.7 KB to ~267.1 KB raw; initial HTML-linked assets dropped from ~714.9 KB to ~696.3 KB raw.

Route-scoped CSS phase 2:
- Removed the obsolete historical Home IA/Depth/Commercial CSS that no longer matches the current Tailwind Home implementation.
- Moved Route product/depth/off-day CSS into the lazy Visitor Route chunk.
- Moved shared depth keyframes into the lazy Living design-system CSS used by Route/Customers/Reports.
- Initial CSS dropped from ~267.1 KB to ~222.1 KB raw; initial HTML-linked assets dropped from ~696.3 KB to ~651.3 KB raw.
- The performance budget was ratcheted down so this reduction cannot silently regress.
