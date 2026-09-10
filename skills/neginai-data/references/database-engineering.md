---
name: negin-database-engineering
description: "Design and optimize database access for SQL Server, PostgreSQL and ClickHouse. Use for schemas, queries, indexes, analytical modeling and performance diagnosis."
compatibility: "Agent Skills compatible clients, including ChatGPT/Codex where Skills are enabled. May use approved MCP/app tools when available."
metadata:
  bundle: "negin-agents-specialist-skills"
  version: "1.0.0"
  category: "engineering"
---

# Purpose

Specialist workflow for correct and efficient database engineering with production safeguards.

# Inputs

- Repository/system context
- Requested behavior or failure
- Runtime/version constraints
- Available tests, logs or acceptance criteria

# Workflow

1. Classify environment before action.
2. Confirm query correctness before optimization.
3. Inspect execution evidence where available.
4. Reduce scanned data and unnecessary joins.
5. Benchmark before and after changes.

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
