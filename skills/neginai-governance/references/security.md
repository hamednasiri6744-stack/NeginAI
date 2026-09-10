---
name: negin-security-engineering
description: "Review and improve application security. Use for trust boundaries, secrets, input validation, authentication, authorization, dependency risk and secure coding."
compatibility: "Agent Skills compatible clients, including ChatGPT/Codex where Skills are enabled. May use approved MCP/app tools when available."
metadata:
  bundle: "negin-agents-specialist-skills"
  version: "1.0.0"
  category: "engineering"
---

# Purpose

Specialist workflow for application security analysis and remediation.

# Inputs

- Repository/system context
- Requested behavior or failure
- Runtime/version constraints
- Available tests, logs or acceptance criteria

# Workflow

1. Identify assets and trust boundaries.
2. Map attacker-controlled inputs.
3. Check authentication and authorization separately.
4. Review secret handling and logs.
5. Verify remediations with negative tests.

# Guardrails

- Inspect before modifying and prefer minimal, reversible changes.
- Preserve unrelated work, existing structure and public contracts unless change is intentional.
- Do not expose secrets, credentials or sensitive configuration in output or logs.
- Do not claim success without verification evidence when verification is available.
- Treat destructive, production or security-sensitive operations as separately governed actions.

# Output contract

Return the implementation/diagnosis summary, files or components affected, verification evidence, important risks and the next action if anything remains.

# Final checks

- Run the narrowest relevant verification first.
- Review the final diff/state.
- Check error/failure paths.
- Report anything not verified.

# Completion rule

Do not report completion until the requested result is produced and the relevant checks have been performed or explicitly identified as unavailable.
