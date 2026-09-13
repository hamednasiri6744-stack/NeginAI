# NeginAI Visitor — Enterprise Integrity Hardening v0.16

## Purpose
Close the highest-risk product-integrity problems found in the v0.15 strict audit without changing backend/API/DB/NGT/Varanegar/Neshan/native integration contracts.

## P0 changes
1. **Authentication boundary**
   - Full document load always begins unauthenticated.
   - Protected Visitor routes redirect to Login.
   - Persistent `localStorage` session bypass removed.
   - Login/logout clear transient business state until a real server identity exists.

2. **Order transaction integrity**
   - Empty cart for a new order.
   - In-progress order workspace survives internal navigation.
   - Active Visit locks the order customer.
   - Customer switching with cart contents requires confirmation and clears the cart.
   - Cross-customer draft restore is blocked during an active Visit.

3. **Visit / Order lifecycle**
   - Resolved route stops cannot be started again.
   - Sale outcome enters Order; it does not claim registration.
   - A pending order can be saved as draft and the Visit can finish with a truthful pending-draft outcome.
   - No-order/no-visit outcomes are explicitly local until server sync exists.

4. **Action integrity**
   - Negin AI quick prompts are consumed.
   - Reports deep-link into Negin AI.
   - Chat send direction fixed.
   - Chat Home control has explicit navigation affordance.

5. **Shared state**
   - Notification read state and badges share one provider.
   - Route visit counts remain shared between Home/Route and today's report visit count.

## Production boundary
This release deliberately does not pretend to provide real authentication or order submission. Client guards are UX/integration boundaries only. Server-side auth, NGT order submission and authoritative data remain mandatory before production.
