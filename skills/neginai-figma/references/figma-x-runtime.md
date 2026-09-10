# Figma-X

Figma-X is the controlled Figma capability layer for the NeginAI Agents Lab.

## Goal
Remove dependence on whether a specific ChatGPT conversation exposes `@Figma`.

`UX-X → Figma-X MCP → Figma REST (read) + Figma Plugin API bridge (write) → Code-X → NeginAI runtime → UX-X QA → Owner approval`

UX-X remains Design Authority. Figma-X supplies governed Figma execution. Code-X maps approved design-system artifacts to code. Negin-Master owns integration, governance and final verification.

## Read plane
The Node service calls official Figma REST endpoints using `FIGMA_ACCESS_TOKEN`. The token is read from environment only and is never returned or logged.

## Write plane
Canvas mutations are never arbitrary JavaScript. `figma_x_apply_operations` accepts a narrow typed allowlist, validates file/mutation policy, persists an idempotent operation, and the locally imported Figma plugin polls the broker and executes via the Figma Plugin API.

## Safety plane
- localhost bind by default
- `READ_ONLY` default
- allowlisted file keys for writes
- explicit owner approval for protected reference files
- no delete/bulk destructive operations in Phase 1
- dry-run
- idempotency keys + correlation IDs
- durable journal/checkpoints
- rollback only when safe inverse operations were captured
- secret redaction
- no `eval`, `new Function`, or arbitrary-JS tool

## MCP tools
`figma_x_status`, `figma_x_capabilities`, `figma_x_auth_status`, `figma_x_file_get`, `figma_x_nodes_get`, `figma_x_images_get`, `figma_x_bridge_status`, `figma_x_checkpoint_create`, `figma_x_apply_operations`, `figma_x_operation_status`, `figma_x_rollback`.

## Initial plugin operations
Inspection: `inspect_selection`, `inspect_node`

Creation: `create_frame`, `create_text`

Layout/style: `set_fills_solid`, `set_strokes_solid`, `set_corner_radius`, `set_auto_layout`, `set_padding`, `set_item_spacing`, `set_opacity`, `rename_node`

Variables: `create_variable_collection`, `create_variable`, `set_variable_value`, `bind_variable_to_fill`

## Local setup
1. Set `FIGMA_ACCESS_TOKEN` for REST reads.
2. Set `FIGMA_X_BRIDGE_TOKEN` to a separately generated local secret.
3. Use `FIGMA_X_MUTATION_MODE=DESIGN_SANDBOX_WRITE` only for an approved sandbox.
4. Set `FIGMA_X_ALLOWED_FILE_KEYS` to the allowed file key(s).
5. Run `node server/index.js`.
6. In Figma Desktop import `plugin/manifest.json` as a development plugin.
7. Run **Configure local bridge**, store the bridge token locally, then run **Run local bridge**.

The development manifest restricts network access to local port 8784 via `devAllowedDomains`.

## Verification
Run:
- `node --check server/index.js`
- `node --check server/policy.js`
- `node --check server/rest-client.js`
- `node --check server/bridge-store.js`
- `node --check plugin/code.js`
- `node tests/test.js`

## Current status
Phase 1 scaffold is `PARTIAL / NEEDS_VALIDATION` until real Figma REST auth, a Figma sandbox plugin run, UX-X MCP wiring, and final security/owner approval for any public domain are verified.

No live Figma connectivity is claimed by the scaffold alone.
