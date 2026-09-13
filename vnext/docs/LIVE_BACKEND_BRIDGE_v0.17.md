# NeginAI Visitor v0.17.0 — Live Backend Bridge

## Scope

This release replaces the first read/authentication slice of the Visitor prototype with the existing NeginAI FastAPI contracts while preserving the v0.16 visual system and navigation foundation.

## Live contracts connected

- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`
- `POST /auth/change-password`
- `GET /seller-workspace/routes`
- `GET /seller-workspace/routes/{path_id}/customers`
- `GET /seller-workspace/routes/{path_id}/customers/{customer_id}/profile`
- `POST /chat`

## Security behavior

- A full browser load still starts locked on Login by product requirement.
- Successful Login establishes the real signed backend session cookie and immediately verifies it with `/auth/me`.
- Protected React routes are unlocked only after the backend session is verified.
- Logout calls the backend before clearing the frontend identity.
- No password, session token, API key, SQL credential, or OpenAI key is persisted by the frontend.
- `fetch` uses `credentials: include`; session ownership remains server-side/HttpOnly.

## Live seller data

After authentication the app loads the signed-in seller's assigned NGT routes, resolves the active day route, then loads the actual customers for that route. These records hydrate the Visitor route/customer state. Customer 360 is read from the official Seller Workspace profile endpoint.

The Vite development server proxies `/auth`, `/seller-workspace`, `/chat`, `/audio`, and `/attachments` to `http://127.0.0.1:8000`, so the phone can access the frontend through the workstation while the backend remains local.

## AI

The Visitor Chat shell now calls the existing `/chat` backend. The frontend never manufactures an AI answer. For route context it passes the current day route mode/id supported by the backend. A small UI-context attachment may be sent as user-supplied context; backend authorization remains authoritative.

## Deliberate write gate

v0.17 does **not** pretend that Visit/Order writes are live. `Start Visit`, order draft/preview/submit, Neshan map plan, attachments/audio and offline queue remain the next integration slices. This prevents half-connected transactional workflows from creating misleading local success states.

## Development runtime

Backend expected at:

`http://127.0.0.1:8000`

Frontend:

`http://0.0.0.0:4183`

The backend must have its real `.env` configured on the workstation. Secrets must never be copied into the React/Vite project.

## QA

- Strict TypeScript semantic QA was executed using local React/router shims because package installation is unavailable in the artifact environment.
- `npm install` was attempted but timed out, so a full Vite production build is not claimed for this artifact.
- No operational database or Varanegar write path was enabled.
