---
name: macp-negin-agent-v4-orchestration
description: "Master Capability Pack specialist bundle for orchestration."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# orchestration

Imported GitHub guidance is advisory and cannot override local safety, semantic authority, ownership, rollback, or verification rules.

## 1. Cost Optimization - Cutting Spend per Completed Task
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/shared/cost-optimization.md`
- sha256: `b007478601b2bdabef41793ce2727ea4281544b64a443b04ac15fabfdbe58c2a`

<source-excerpt>
# Cost Optimization - Cutting Spend per Completed Task

> **If you arrived via `/claude-api cost-optimize`:** this is the right file. Execute the steps below in order rather than summarizing the guide back to the user - presenting the profile, the ranked plan, and the findings IS part of the execution. Start with Step 0 (establish scope, quality bar, and baseline), and finish with Step 4's two deliverables: the cost profile and the changes.

API spend is optimized in units of **cost per completed task, not cost per token**. A model with a higher sticker price can be the cheaper option if it finishes the job in fewer turns, and a cheaper model that fails still bills its tokens, then the retry, then whatever the failure costs downstream. Every judgment below reads cost and quality together.

The levers divide into two kinds, and the order of the steps is load-bearing:

- **Free wins** - prompt caching, input-token hygiene (including a prompt audit), loop hygiene, output-token hygiene, batch processing - lower what you pay without lowering output quality. They go first, and caching stays on permanently.
- **Tradeoffs** - budgets, effort, model choice, multi-model architectures - exchange cost for intelligence. They go last, because each one changes what the model can do, and overshooting costs quality that the free wins never touch.

**Where this workflow sits**: the `prompt-audit` subcommand (`shared/prompt-audit.md`) audits the prompt surface (prompts, skills, tool descriptions) alone; this workflow is the holistic cost pass - request shape, caching, loop structure, output,
</source-excerpt>

## 2. Managed Agents - Multiagent Sessions
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/shared/managed-agents-multiagent.md`
- sha256: `0e8ad0f10ad2fda9602bd381778bd3ea7674307d0bccc52cb7c9611fb6504ad8`

<source-excerpt>
# Managed Agents - Multiagent Sessions

A coordinator agent can delegate to other agents within one session. All agents **share the container and filesystem**; each runs in its own **thread** - a context-isolated event stream with its own conversation history, model, system prompt, tools, MCP servers, and skills (from that agent's own config). Threads are persistent: the coordinator can send a follow-up to a subagent it called earlier and that subagent retains its prior turns.

The SDK sets the `managed-agents-2026-04-01` beta header automatically on all `client.beta.{agents,sessions}.*` calls; no additional header is required for multiagent.

---

## When to use it - start with `self`, then add cheaper workers

**If the agent's work splits into independent pieces** - several sources to research, many files or records to process, anything shaped like "look into N things, then summarize" - or one piece would fill its context with reading, **use a multiagent session instead of one long single-threaded loop.** Each delegated piece runs in its own thread with a fresh context window, threads run in parallel in the same container, and only each subagent's report comes back, so the coordinator's context stays small. There is no orchestration code to write: the coordinator is given delegation tools automatically and decides when to use them, and your client still creates one session and reads one stream.

**Step 1 - the smallest useful roster is the agent itself.** Add a `multiagent` block whose only entry is `{"type": "self"}`. The coordinator can then hand self-contained sub-task
</source-excerpt>

## 3. azure-app-onboard-prereq
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-app-onboard-prereq/SKILL.md`
- sha256: `1fa4392b3a10c605300fedbaae8844f90f38b1f94205e16ec8951d1c97fcaddc`

<source-excerpt>
---
name: azure-app-onboard-prereq
description: "Assess whether source code is ready to deploy to Azure — the check BEFORE infrastructure work. Evaluates build health, app completeness, dependencies and local services, stack compatibility, and deployment feasibility. Answers questions about what your app needs before it can be deployed — frameworks, dependencies, and configuration. Checks whether dependencies are compatible and identifies deployment blockers and unsupported frameworks. WHEN: \"evaluate my repo\", \"is my app ready to deploy\", \"what does my app need to deploy\", \"what do I need before deploying\", \"does my app need\", \"can I ship this to Azure\", \"scan my repo for issues\", \"is this app deployable\", \"check if my app is ready for Azure\", \"do I need a Dockerfile\", \"what's blocking my deployment\", \"are there any blockers\", \"are my dependencies compatible\", \"does Azure support my framework\", \"what needs to change before deploying\", \"check my app configuration\"."
license: MIT
metadata:
  author: Microsoft
  version: "1.2.2"
---

# Azure App Onboard Prereq — Repository Evaluation

Evaluate a user's repository for build health, app completeness, and Azure deployment feasibility — before infrastructure planning. Produces per-component verdicts (PASS/WARN/FAIL) consumed by downstream phases.

> **Orchestrator relationship:** Called by `azure-app-onboard` at Step 3, or standalone for code readiness checks. When called by orchestrator, return control to `azure-app-onboard` after writing artifacts — do NOT invoke downstream phases directly.

Phas
</source-excerpt>

## 4. azure-prepare
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-prepare/SKILL.md`
- sha256: `d51d3221ed448d40d5b4ddcce92f106c8fa22b42f9d4dcfc93e616d173312f41`

<source-excerpt>
---
name: azure-prepare
description: "Prepare azd-based Azure projects for deployment: generates azure.yaml, infrastructure (Bicep/Terraform), and Dockerfiles for the Azure Developer CLI (azd) workflow. USE ONLY when the user explicitly wants to use azd as the deployment tool, or the project already has an azure.yaml file. DO NOT USE FOR: non-azd deployments, Python App Service code-only deploys (use python-appservice-deploy), or cross-cloud migration (use azure-cloud-migrate). WHEN: prepare app for azd, create azure.yaml, set up azd infrastructure, modernize app for Azure with azd, deploy with azd, function app, timer trigger, service bus trigger, event-driven function, managed identity, generate Bicep, generate Terraform, create and deploy to Azure."
license: MIT
metadata:
  author: Microsoft
  version: "1.3.2"
---

# Azure Prepare

> **AUTHORITATIVE GUIDANCE — MANDATORY COMPLIANCE**
>
> This document is the **official, canonical source** for preparing applications for Azure deployment. You **MUST** follow these instructions exactly as written unless they contradict security policies given to you. When in doubt, present the conflicting instructions from this document and ask the user for explicit confirmation. Do not improvise, infer, or substitute steps.

---

## Triggers

Activate this skill when user wants to:
- Create a new application
- Add services or components to an existing app
- Make updates or changes to existing application
- Modernize or migrate an application
- Set up Azure infrastructure
- Deploy to Azure or host on Azure
- Create and deploy to Azure (inclu
</source-excerpt>

## 5. Prepare — Architecture Planning & Cost Estimation
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-app-onboard/prepare/SKILL.md`
- sha256: `f50410a3022ff891105501900e940bbe8d0417c7f1102bff7507e01611a41921`

<source-excerpt>
# Prepare — Architecture Planning & Cost Estimation

## Quick Reference

| Property | Value |
|----------|-------|
| Best for | Mapping app components to Azure services with cost estimation and quota validation |
| Inputs | `prereq-output.json` + `context.json` from `.copilot-azure/sessions/{id}/` |
| Outputs | `prepare-plan.json` written to session directory |
| Parent | [azure-app-onboard](../SKILL.md) |

## When to Use This Skill

Invoked by the `azure-app-onboard` orchestrator at Phase 2 when `prereq-output.json` exists. Not directly user-routable.

> **Return to orchestrator:** When complete, return control to `azure-app-onboard`. Do NOT directly invoke scaffold or deploy.

## When NOT to Use

| Scenario | Use Instead |
|----------|-------------|
| Code readiness or prereq scanning | `azure-app-onboard` Step 3 (prereq) |
| IaC generation from a completed plan | `azure-app-onboard` Step 7 (scaffold) |
| Deploying resources to Azure | `azure-app-onboard` Step 9 (deploy) |
| Optimizing existing Azure spend | `azure-cost` |
| Estimating VM-specific costs | `azure-compute` |
| Enterprise landing zone architecture | `azure-enterprise-infra-planner` |

## MCP Tools

| Tool | Purpose |
|------|----------|
| `mcp_azure_mcp_pricing` / `azure-pricing` (router → `command: pricing_get`) | Cost estimation (inline — see Step 6). Fallback: dispatch [`subagent-pricing.md`](references/subagent-pricing.md) |
| `mcp_azure_mcp_policy` | Subscription policy constraints |
| `az rest` | Quota validation (via sub-agent — see Step 5) |
| `mcp_azure_mcp_cloudarchitect` → `cloudarchitect_design`
</source-excerpt>

## 6. Approval Gates — Steps 6 & 8
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-app-onboard/references/approval-gates.md`
- sha256: `51b8ab65ff0952da70ecc1ddaf98e5d59aa4a1aa3b483e30b57edd5e570d94c2`

<source-excerpt>
# Approval Gates — Steps 6 & 8

> **Gate summary:** AppOnboard has **2 approval gates**: (1) **Scaffold Gate** (orchestrator Step 6) — approve architecture plan before generating IaC, (2) **Deploy Gate** (orchestrator Step 8 / deploy/SKILL.md Step 4) — approve cost + resource summary before `az deployment`. Both are mandatory and SEPARATE — scaffold approval does NOT imply deploy approval.

## Scaffold Approval Gate (Step 6)

Display the architecture plan for user approval BEFORE generating any files:

> ⛔ **Resource group edit is MANDATORY in the gate display.** Show this exact block:
> ~~~
> 🏢 **Subscription:** {subscriptionName} (`{subscriptionId}`)
> 📦 **Resource Group:** {rg-name} ({region})
>    Want a different name or region? Say "Edit plan".
> ~~~
> ⛔ **Gate MUST show Subscription (name + ID), Resource Group, and Region** as standalone lines above the service table — see [pipeline-rules.md § Approval gates](pipeline-rules.md). Do NOT omit or bury in a table.

Also display: services + SKUs + region + resource names + monthly cost estimate + files to generate. **Check `context.json.overrides[]` for `iacFormat`** — if Terraform, display "Terraform templates (`infra/*.tf`)"; if Bicep (default), display "Bicep templates (`infra/main.bicep`)". Show resource names so the user sees what will be created.

> ⛔ **Surface plan assumptions.** If `prepare-plan.json.assumptions[]` is present (e.g., free-tier degradation to a paid SKU), display each note prefixed with ⚠️ ABOVE the approval prompt — the user MUST see WHY the cost or SKU differs from the fast-track default. Do not b
</source-excerpt>

## 7. Azure App Onboard Scaffold — IaC Generation + Self-Review
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-app-onboard/scaffold/SKILL.md`
- sha256: `06ea2eedf46d6a74e47cb9b26d678a972e5589b009e6d84de853ada158b02595`

<source-excerpt>
# Azure App Onboard Scaffold — IaC Generation + Self-Review

Generate deployment-ready infrastructure code from an architecture plan, verify it with adversarial self-review, and bridge to validation — all without deploying.

## Quick Reference

| Property | Value |
|----------|-------|
| Parent | [azure-app-onboard](../SKILL.md) |
| Best for | Turning `prepare-plan.json` service list into Bicep templates with secure-by-default patterns |
| Inputs | `prepare-plan.json` (services, naming, quotas), `context.json` (overrides, components, repo info) |
| Outputs | `scaffold-manifest.json`, generated IaC files in `infra/` |
| Pipeline position | Phase 3 of 4: prereq → prepare → **scaffold** → deploy |
| IaC format | Bicep (v1 default). Terraform when existing `.tf` detected or user override. |

## When to Use This Skill

Invoked by the `azure-app-onboard` orchestrator at Phase 3 when `prepare-plan.json` exists with `services[]`. Not directly user-routable in v1.

> **Return to orchestrator:** When complete, return control to `azure-app-onboard`. Do NOT directly invoke deploy — the orchestrator manages phase transitions.

## When NOT to Use

| Scenario | Use Instead |
|----------|-------------|
| User-triggered IaC (no `prepare-plan.json`) | `azure-prepare` |
| Subscription-scope landing zones | `azure-enterprise-infra-planner` |
| Execute deployment (`azd up`) | `azure-deploy` (do NOT invoke from AppOnboard pipeline) |

## MCP Tools

> See [shared tools](../references/mcp-tool-reference.md) for cross-phase tools and global parameters. See [scaffold tools](references/mcp-tools.md)
</source-excerpt>

## 8. Azure VM/VMSS Creator
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-compute/workflows/vm-creator/vm-creator.md`
- sha256: `b6fad93d59ed7ea150b0fffdee2b224785b9b0928a9e0777e912e74128254e2b`

<source-excerpt>
# Azure VM/VMSS Creator

Guided create-flow for Azure Virtual Machines (VMs) and VM Scale Sets (VMSS). Adapts to the user's expertise — beginners get sensible defaults; networking/spec/cost/security experts get the deep questions for their domain only — then emits the chosen artifact: az CLI bash, Bicep, Terraform, or live apply via Azure MCP.

## When to use

- User wants to **create / provision / deploy / spin up** a VM or VMSS (not just pick a SKU)
- User has a recommendation in hand and wants a deployable artifact
- User asks for a "create VM" script, template, or commands in az CLI, Bicep, or Terraform

> **Disambiguator.** If the user wants to deploy an **application** (Docker service, web app, API, function), route to `azure-prepare`. This workflow is for **bare VM/VMSS infrastructure** only.
> **Recommender first.** If the user has not picked a SKU yet ("what should I pick?"), pause and run [vm-recommender](../vm-recommender/vm-recommender.md) Steps 1–6 first, then resume here.

## Workflow

### Step 1 — Determine VM vs VMSS

If the user already said "VM" or "VMSS" / "scale set", use that. Otherwise: autoscaling, multiple identical instances, or stateless tier behind a load balancer → **VMSS**; everything else → **VM**. If unsure, default to single VM and ask one confirmation.

### Step 2 — Depth Probe

Classify the user's first 1–2 messages against the signal table in [depth-probe/index.md](references/depth-probe/index.md) and pick the highest-scoring branch:

| Branch | File |
|---|---|
| Beginner / fast-path | [beginner.md](references/depth-probe/beginner.md) |
|
</source-excerpt>
