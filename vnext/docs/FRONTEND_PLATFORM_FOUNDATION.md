# NeginAI vNext Frontend Platform Foundation

Status: PARTIAL / IMPLEMENTED FOUNDATION / NEEDS END-TO-END VALIDATION

## Canonical boundary

The existing NeginAI backend remains authoritative for authentication, seller workflows,
pricing, discount, gift, credit, tax, inventory semantics, KPI semantics, and order submission.

The frontend owns presentation, interaction, client routing, request lifecycle, local UI state,
and workflow orchestration only.

## Implemented

- Central route registry (`src/app/routes.tsx`)
- Shared provider layer (`src/app/AppProviders.tsx`)
- TanStack Query client (`src/lib/query/client.ts`)
- Backward-compatible `useApiQuery` adapter backed by TanStack Query
- Configurable API client with same-origin default, credentials, timeout/abort handling,
  request-id propagation through `ApiError`, and normalized network/HTTP failures
- Global render error boundary
- Offline network indicator
- Existing session-cookie hauth boundary retained
- Existing Seller route endpoint retained: `GET /seller-workspace/routes`

## Verified backend contracts used by vNext

- `GET /auth/me`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /seller-workspace/routes`

All other seller/previsit/order contracts should be added only after their exact response shapes
are mapped from the backend implementation/tests/OpenAPI. Do not duplicate commercial calculations
in the browser.

## NEEDS_VALIDATION

- Production frontend origin/base URL policy
- Exact AuthProfile schema/role vocabulary
- Seller route response schema beyond fields currently rendered
- Role-to-module visibility matrix
- Cross-origin credential/CORS policy if vNext is ever served separately from the API
- PWA/offline business-data persistence policy

## Next implementation slice

Seller Stage 1:
1. My Routes
2. Day Route
3. Route Customers
4. Customer profile / Customer360
5. Visit workspace
6. Previsit context
7. Draft/save/preview
8. Commercial validation from backend
9. Visit completion

Each step must use the existing backend contract and preserve server-side business semantics.
