# NeginAI Living Layer

Canonical behavioral layer for motion, physical feedback, live-state signaling and data-driven reactions.

## States
- `idle`: visually stable.
- `ambient`: very slow breathing only.
- `live`: connected to real live data.
- `updating`: actively syncing/fetching.
- `changed`: a real value/state changed.
- `attention`: short, rare attention cue.
- `active`: current/selected operational object.

## Rules
- Idle screens stay calm; motion is never constant noise.
- Real data changes may trigger a short 320–760ms reaction.
- Continuous pulse is reserved for genuinely live/updating states.
- Touch feedback is fast and physical; decorative sweeps are rare.
- Product screens consume tokens/classes; they do not invent motion timings.
- `prefers-reduced-motion` is mandatory.
- No KPI meaning or backend semantics live in this layer.

## Rollout gate
- A screen opts in with `.ng-living-root[data-living-ui="on"]`.
- With `data-living-ui="off"`, Living primitives are inert.
- Current first consumer: Visitor Home pilot.
- New screens must reuse this layer rather than copy Home-specific animation CSS.
