# NeginAI vNext Dev Runtime

## Public preview

- URL: `https://dev.hagents.ir`
- Cloudflare tunnel: `neginai-dev`
- Tunnel transport: `http2` (QUIC/UDP 7844 is blocked on the current network)
- Origin: `http://127.0.0.1:4180`

## Frontend

- Runtime: Vite dev server with HMR
- Listener: `127.0.0.1:4180`
- Persistence: Windows Scheduled Task `NeginAI vNext Frontend`
- Source: `D:\Projects\NeginAI\vnext`

## Backend

- Runtime: FastAPI/Uvicorn
- Listener: `127.0.0.1:8001`
- Persistence: Windows Scheduled Task `NeginAI Local Dev Server`
- Source: `D:\Projects\NeginAI`

## Same-origin API proxy

Vite proxies these paths to `http://127.0.0.1:8001`:

- `/auth`
- `/seller-workspace`
- `/audio`
- `/health`

## Tunnel persistence

- User Startup launcher: `NeginAI-dev-tunnel.cmd`
- Cloudflared config: `C:\Users\Sys\.cloudflared\neginai-dev.yml`
- Only one local `cloudflared` process should reference `neginai-dev.yml`.
- Windows Scheduled Task registration for the tunnel requires elevated rights on this workstation, so persistence uses the current-user Startup folder instead.

## Verification

- `https://dev.hagents.ir/` must return HTTP 200 and load the Vite client.
- `https://dev.hagents.ir/health` must return HTTP 200 with NeginAI liveness JSON.
- `/auth/me` without a valid session should remain protected.

This environment is the live vNext development preview. It is not production.
