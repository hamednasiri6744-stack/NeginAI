# NeginAI Enterprise Hardening v0.15.0

Scope: contextual Negin AI Chat Shell. No production AI, backend, database, NGT, Varanegar, Neshan or Android bridge contract was changed.

## Closed in this release

1. The Home `Negin AI` control is no longer a dead-end toast; it opens a real route: `/visitor/ai`.
2. The AI surface carries explicit context (`home`, `route`, `customer`, `order`) and preserves customer/visit/draft identifiers when available.
3. Customer 360, Route and Order Workspace have contextual AI entry points.
4. Composer, quick prompts, file/camera/voice affordances and conversation surface exist as UI architecture.
5. The prototype does **not** fabricate AI answers. User messages are kept only in local component state and the UI clearly reports that the service is not connected.
6. Existing backend/native capabilities remain reserved for Integration. No fake success, fake upload, fake voice transcription or fake enterprise data was added.

## Next P0 targets

- Replaceable authentication/session boundary.
- React-side Neshan/native navigation bridge without removing current operational capabilities.
- Authoritative NGT order submit contract + idempotency.
- Offline queue/sync engine.
