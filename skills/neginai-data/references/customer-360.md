---
name: negin-customer-360
description: "Build a consolidated analytical view of a customer from authorized enterprise data. Use for sales, returns, receivables, visits, product mix, activity changes, risks and opportunities."
compatibility: "Agent Skills compatible clients, including ChatGPT/Codex where Skills are enabled. May use approved MCP/app tools when available."
metadata:
  bundle: "negin-agents-specialist-skills"
  version: "1.0.0"
  category: "business"
---

# Purpose

Specialist workflow for customer identity resolution and cross-domain customer analysis.

# Inputs

- Objective/question
- Relevant approved data and business context
- Time range/scope
- Definitions, targets or constraints if applicable

# Workflow

1. Resolve canonical customer identity.
2. Collect only relevant authorized dimensions.
3. Align time windows and metric definitions.
4. Summarize sales, returns, receivables, visits and product mix.
5. Label inferred insights and confidence.

# Guardrails

- Use approved enterprise sources and state data freshness and scope.
- Production ERP/SQL access is read-only by default; do not perform DML, DDL, non-read EXEC, or configuration changes.
- Do not invent missing definitions, targets, transactions or business facts.
- Separate observed facts, calculations, hypotheses, forecasts and recommendations.
- Minimize unnecessary personal, financial and employee-level data.

# Output contract

Return a concise executive result first, followed by evidence, material findings, uncertainty, provenance/freshness and next actions.

# Final checks

- Reconcile important totals and filters.
- Check time range, units and scope.
- Flag stale/incomplete data.
- Ensure each material claim has supporting evidence.

# Completion rule

Do not report completion until the requested result is produced and the relevant checks have been performed or explicitly identified as unavailable.
