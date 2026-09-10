---
name: negin-pricing-promotion-intelligence
description: "Analyze pricing, discounts, promotions and product-mix effects. Use for price history, discount anomalies, promotion effectiveness and campaign comparisons."
compatibility: "Agent Skills compatible clients, including ChatGPT/Codex where Skills are enabled. May use approved MCP/app tools when available."
metadata:
  bundle: "negin-agents-specialist-skills"
  version: "1.0.0"
  category: "business"
---

# Purpose

Specialist workflow for pricing, discount and promotion performance analysis.

# Inputs

- Objective/question
- Relevant approved data and business context
- Time range/scope
- Definitions, targets or constraints if applicable

# Workflow

1. Define baseline and promotion windows.
2. Separate price, volume, mix and promotion effects where possible.
3. Detect abnormal discounts or inconsistent application.
4. Compare segments and periods.
5. Avoid causal claims not supported by evidence.

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
