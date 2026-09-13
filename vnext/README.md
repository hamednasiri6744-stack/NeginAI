# NeginAI Cumulative Visitor v0.17.0

Enterprise Integrity Hardening on top of the cumulative mobile-first Visitor application.

## Routes
- `/` Login
- `/visitor/home` Visitor Home
- `/visitor/ai` Negin AI contextual chat shell
- `/visitor/route` Route / Visit
- `/visitor/orders` Orders / Catalog / Cart
- `/visitor/orders/history` Drafts / Order History / Invoice Preview
- `/visitor/reports` Reports / KPI
- `/visitor/notifications` Notifications / Alerts
- `/visitor/profile` Profile / Settings / Logout
- `/visitor/customers` Customers
- `/visitor/customers/:customerId` Customer 360

## v0.17.0 enterprise integrity hardening
- Every full application load starts behind Login. Direct protected URLs and browser refreshes cannot reopen the Visitor workspace without passing the Login boundary again.
- Removed the previous persistent `localStorage` visitor-session bypass. Until the real auth API is connected, authorization state is deliberately memory-only.
- Login and Logout clear transient customer/order/visit/draft/scroll/notification state so one local user cannot inherit another user's in-progress workspace.
- New orders start with an empty cart; no product quantities are silently prefilled.
- Unsaved Order Workspace state is session-persisted across internal navigation, so opening Negin AI and returning does not discard the current cart/payment/order-type context.
- During an active Visit, the order customer is locked to the visit customer.
- Changing customer outside a Visit requires explicit confirmation when the cart is non-empty, and clears the cart to prevent cross-customer order contamination.
- Completed/skipped route stops cannot be started again.
- Visit -> Sale -> Order no longer loops indefinitely: the user can save the pending order as a draft and complete the visit truthfully as “visit completed / order draft pending”.
- No-order/no-visit results explicitly state that the result is local until server integration is connected.
- Order review no longer presents a fake successful registration; final server/NGT submission remains visibly unavailable.
- Drafts are no longer seeded fake records and are cleared on logout/login boundary changes.
- Notification read state and header badge now share one in-app source of truth.
- Report “تحلیل بیشتر” opens the real Negin AI chat shell instead of a dead toast.
- Home AI prompt links are now consumed by the chat shell.
- Negin AI send icon direction is corrected and Home is a real, visually identifiable navigation control.
- Developer-facing route/draft identifiers were removed from the user-facing chat UI.
- Login input autofill/focus styling is hardened so the native white input strip does not replace the dark field surface.
- Profile version display is synchronized to `0.17.0`.

## Still intentionally unresolved
- Server-backed authentication, session expiry, token refresh, permissions and identity validation.
- Real Negin AI model/tool backend.
- Real Neshan/GPS/reroute/native navigation bridge in the React replacement.
- Real NGT/Varanegar order submission, idempotency and authoritative price/tax/discount/gift response.
- Real offline queue/cache/sync engine.
- Several secondary action shells remain to be productized (customer edit/new customer, advanced filters, PDF service, password recovery/change, dialer/GPS integrations).
- Sales/order/report history data is still local fixture data until authoritative backend contracts are connected.

## Safety / integration
- Backend, API, DB, NGT, Varanegar, Neshan and Android Bridge contracts are not modified in this release.
- No direct write to Varanegar/SQL is introduced.
- Client-side Login is only an integration boundary, not real security. Real authorization must be enforced server-side before production.

## Run
```powershell
npm.cmd install
npm.cmd run dev
```


## v0.17.0 — Live Backend Bridge

See `docs/LIVE_BACKEND_BRIDGE_v0.17.md`. Authentication, seller route/customer read models, Customer 360 and Negin AI chat now use the existing FastAPI backend contracts. Transactional Visit/Order writes remain intentionally gated until the next integration slice.
