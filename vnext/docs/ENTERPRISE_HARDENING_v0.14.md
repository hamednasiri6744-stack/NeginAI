# NeginAI Enterprise Hardening v0.14.0

Scope: Navigation & State Foundation only. No production backend/API/DB contracts were changed.

## Closed in this release

1. **Back regression**
   - Customer 360 uses internal history-aware Back.
   - Direct deep-link entry falls back to Customers instead of exiting unpredictably.

2. **Lost Customer list state**
   - `q` and `status` live in the URL.
   - In-screen changes replace the current history entry.
   - Scroll position is restored per history entry.

3. **Broken Customer -> Visit context**
   - Customer ID is passed into Route.
   - Route selects the matching stop by `customerId`, not by reusing stop IDs.

4. **Broken Visit -> Order context**
   - Active visit carries `routeId`, `customerId`, `visitId`, `startedAt`.
   - “Sale / Order” continues into Orders instead of declaring a sale complete.

5. **Cross-screen route contradiction**
   - Home and Route share one session-scoped route state and progress calculation.

6. **Fake order success**
   - The prototype no longer claims NGT/Varanegar registration.
   - Submit stops at a truthful “ready to send” boundary.

7. **Split draft truth**
   - Order Workspace and Archive now share one session draft source.

8. **Fake Sync success**
   - Manual Sync explicitly says no API/queue transmission occurred.

## Next P0 hardening targets

- Real/replaceable auth boundary.
- Negin AI chat shell + contextual entry points.
- Real React-side Neshan/navigation bridge without removing the existing backend/native capabilities.
- NGT-backed Order submit contract with idempotency and authoritative totals.
- Offline queue/sync engine.

## Migration rule

The existing NGT/Varanegar integration remains authoritative. UI state in this prototype is never a substitute for official pricing, stock, tax, discount, prize, order registration, route/navigation or accounting state.
