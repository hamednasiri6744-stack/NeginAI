---
name: neginai-agent-routing
description: "NeginAI multi-agent skill routing, ownership, handoff, capability boundaries, reconnect-safe upgrades and specialist selection."
license: MIT
---

# NeginAI Agent Routing

Use this skill whenever a task may cross Negin-Master, Code-X, UX-X, Data-X, or Automation-X.

## Canonical routing source

`D:\Projects\NeginAI\skills\AGENT_SKILL_ROUTING.json` is the machine-readable routing matrix. Project-local NeginAI skills are the single source of specialist instructions. A Skill defines knowledge and workflow; it never grants a runtime capability that the target agent does not already have.

## Routing rules

- Negin-Master owns orchestration, canonical business/semantic authority, conflict reconciliation, approval boundaries and final evidence composition.
- Code-X owns implementation, refactoring, build/test/git, MCP engineering and guarded shell work.
- UX-X owns design-system consistency, visual QA, responsiveness, accessibility, Figma workflows and reversible UI modernization.
- Data-X owns analytics, BI, anomaly/forecasting/data-quality work and strict read-only Varanegar analysis under canonical semantics.
- Automation-X owns n8n/Airflow/API/webhook orchestration, retry/idempotency, observability and guarded workflow operations.
- Cross-domain work should load the local agent's highest-scoring routed skills first, then hand off work outside that agent's execution boundary.
- Never infer that a routed skill authorizes database writes, arbitrary shell, credential access, remote mutation or destructive actions.
- For Varanegar/ERP KPIs, canonical semantic authority outranks raw-table inference and live SQL remains read-only.

## Upgrade model

The project skill store is versioned independently from agent runtimes. Agent upgrades should prefer hot reload or reconnect-only activation so updated skills become available without rebuilding unrelated services.

## Completion

A routing decision is complete only when the selected agent is capable of the requested action, the relevant Skill is loaded, boundary-crossing work is handed off explicitly, and the requested postcondition is verified with evidence.
