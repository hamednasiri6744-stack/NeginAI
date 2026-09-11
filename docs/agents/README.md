# NeginAI Engineering Agent Layer

This directory defines the project-specific engineering contract used by the **NeginAI Principal Engineer** and
the deterministic Git guardian.

## Components

- `PROJECT_VISION.md` — project intent and commit-level vision test
- `BUSINESS_INVARIANTS.md` — route-sales, pricing, tax, credit, inventory and logistics guardrails
- `MULTI_AGENT_CONTRACT.md` — non-conflicting collaboration rules for Codex and other agents
- `.github/agents/neginai-principal-engineer.agent.md` — VS Code custom agent
- `scripts/neginai_guardian.py` — local commit auditor
- `.githooks/pre-commit` / `.githooks/post-commit` — repository-local commit monitoring

Guardian reports are written to `artifacts/neginai-guardian/` and are intentionally excluded from Git.

## Manual guardian commands

```powershell
.\.venv\scripts\python.exe .\scripts\neginai_guardian.py manual
.\.venv\scripts\python.exe .\scripts\neginai_guardian.py pre-commit
.\.venv\scripts\python.exe .\scripts\neginai_guardian.py post-commit
```

## VS Code

The custom agent is workspace-scoped under `.github/agents/`.
In VS Code Chat, select **NeginAI Principal Engineer** from the agents list.

This project layer does not grant an AI model background autonomy by itself. The Git guardian runs automatically
on commits; AI coding/reasoning runs when an agent session is active or when the user explicitly invokes it.
