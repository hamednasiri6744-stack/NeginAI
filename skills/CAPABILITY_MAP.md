# NeginAI Project Skill & Capability Map

## Target architecture
ChatGPT -> Code-X (single primary connector) -> `D:\Projects\NeginAI\skills` -> project skill resolver -> optional loopback capability services.

Standalone specialist connectors are not required for normal project work once their knowledge/policies are represented here. Local capability services may remain as implementation details because a Skill is knowledge/workflow, not an external side-effect executor.

## Skill routing
- `neginai-core`: project scope, product identity, execution discipline
- `neginai-governance`: architecture, authority, reconciliation, final evidence rules
- `neginai-ui-ux`: design system, RTL, responsive, accessibility, visual QA
- `neginai-figma`: Figma control plane and design-to-code mapping
- `neginai-frontend`: React/TypeScript frontend engineering
- `neginai-testing`: build, regression, accessibility and runtime evidence
- `neginai-data`: analytics, KPI validation, quality, anomaly, forecasting
- `neginai-varanegar`: Varanegar semantic/read-only policy
- `neginai-automation`: n8n/Airflow/API/webhook orchestration design
- `neginai-shell-ops`: Windows PowerShell/CMD remote execution, timeout handling, process/service diagnostics, MCP and Cloudflare operational reliability

## Local capability services
The registry `skills/_shared/local-capabilities.json` contains only loopback endpoints and external credential-source locations; it stores no credential values. `skills/_shared/scripts/local-mcp-client.mjs` is the controlled client. It redacts secret-like response fields and refuses non-loopback endpoints.

Current service boundaries:
- Figma-X: governed Figma read/write; owner approval required for mutation.
- Data-X: local/read-only analytics and planning; no production SQL.
- Automation-X: static/advisory workflow capability; no direct production mutation.

## Security
Never commit credentials, session cookies, API keys, passwords, access tokens, private keys, or production connection strings into `skills/`. Credentials remain outside the repository.

## Verification rule
A capability is AVAILABLE only after a live health/tool call succeeds. A skill existing on disk proves knowledge availability, not runtime capability availability.
