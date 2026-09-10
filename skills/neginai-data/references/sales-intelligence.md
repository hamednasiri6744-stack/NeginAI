---
name: negin-sales-intelligence
description: "Analyze enterprise sales performance by branch, supervisor, representative, customer, department, product and period. Use for sales KPIs, target gaps, trends, anomalies, drill-downs and evidence-backed commercial actions."
compatibility: "Agent Skills compatible clients, including ChatGPT/Codex where Skills are enabled. May use approved MCP/app tools when available."
metadata:
  bundle: "negin-agents-specialist-skills"
  version: "1.0.0"
  category: "business"
---

# Purpose

Specialist workflow for sales KPIs, targets, trends, mix, contribution and commercial exceptions.

# Inputs

- Objective/question
- Relevant approved data and business context
- Time range/scope
- Definitions, targets or constraints if applicable

# Workflow

1. Confirm KPI semantics and time scope.
2. Use approved analytical sources and state freshness.
3. Compute baseline, variance, trend and contribution.
4. Drill into material drivers only.
5. Separate facts, hypotheses and recommendations.

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
