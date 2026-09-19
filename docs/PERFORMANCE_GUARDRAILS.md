# NeginAI Performance Guardrails

Goal: adding features must not silently degrade startup, navigation, animation smoothness, or background network load.

Current measured production baseline (2026-09-19):
- Initial entry JS: ~340.4 KB raw
- Initial entry CSS: ~222.1 KB raw
- Initial HTML-linked assets: ~629.2 KB raw
- Largest current lazy Visitor feature chunk: ~42 KB raw
- Floating Negin AI chunk: ~10.4 KB raw

Enforced budgets:
- Initial entry JS <= 350 KB
- Initial entry CSS <= 235 KB
- Initial HTML-linked assets <= 640 KB
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

Unused query runtime removed:
- Removed the app-shell QueryClientProvider because no runtime screen imports or uses TanStack Query hooks today.
- The generated API client may still use TanStack Query in the future, but it remains outside the production graph until actually imported.
- Initial JS dropped from ~362.6 KB to ~338.4 KB raw; initial HTML-linked assets dropped from ~651.3 KB to ~627.1 KB raw.

Context render isolation:
- Split notification badge data from the full notification feed, so Home/Route/Orders/Customers/Reports/Profile do not rerender for notification loading/live-connection state when badge values are unchanged.
- Split stable workflow actions, active-visit state, and route summary from the full Route workflow context.
- LiveData, Login and Profile now consume stable workflow actions instead of the full route state.
- Customer and Orders consume only active-visit state; Floating Negin AI consumes only active-visit + route summary while open.
- Navigation distance/ETA updates are transient, skip sessionStorage writes, and bail out when the values are unchanged.

Runtime hot-path cleanup:
- Visit elapsed time no longer drives a React render of the full Route screen every second; the two timer text nodes are updated directly and pause while the document is hidden.
- Auth activity tracking no longer listens to pointermove, and its localStorage idle check is throttled before storage access instead of after it.
- Activity still tracks pointerdown, keydown, touchstart and wheel, preserving idle-session semantics without a high-frequency pointer hot path.


Backend/tour acceleration (2026-09-19):
- Root cause measured: seller route reads were spending ~33 seconds in synchronous operational-notification/SQLite work while the SQL route queries themselves were only a few hundred milliseconds.
- Route-assignment observation and external push delivery are now removed from the seller read hot path.
- Added bounded in-process read cache with optional Redis backing for seller routes, active-route customers, and target pulse.
- Added GET /seller-workspace/tour-bootstrap so Route + active tour customers arrive in one HTTP request instead of a sequential public round trip.
- Visitor startup is snapshot-first: the last successful route/customer snapshot is restored from IndexedDB immediately, then refreshed from live NGT data.
- API JSON responses support gzip and expose Server-Timing for latency diagnosis.
- OpenAI/Agents-heavy automation/chat imports were removed from the normal API startup path and are loaded only when those features are actually used.
- Measured authenticated local HTTP bootstrap: ~371 ms cold and ~17 ms warm; warm backend application time ~13 ms.
- Measured authenticated public bootstrap through vnext.hagents.ir: ~1.36 s cold and ~1.13 s warm from the current remote test host. Cloudflare/origin network transit, not SQL execution, is now the dominant remaining public-path cost.
- Public frontend was verified to serve the build that calls /seller-workspace/tour-bootstrap.


Metadata lock isolation:
- Full schema metadata scans no longer run unconditionally on every API restart when a populated local schema cache already exists.
- Existing schema metadata is reused and the next full scan is deferred until SCHEMA_SYNC_INTERVAL; empty/first-run installs still scan immediately.
- This prevents the large schema cache rewrite from monopolizing SQLite's writer lock during operational startup.
- Verified after restart: operational BEGIN IMMEDIATE remained available after background services started, while the previous startup path reproduced database-is-locked failures.
