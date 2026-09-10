---
name: macp-negin-agent-v4-planning
description: "Master Capability Pack specialist bundle for planning."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# planning

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

## 3. Prompt Audit - Finding and Removing Dated Prompting Patterns
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/shared/prompt-audit.md`
- sha256: `571b08c181a8f3f0906a99045ff0bca88ca728d5a2d01afabb620b270c8048a2`

<source-excerpt>
# Prompt Audit - Finding and Removing Dated Prompting Patterns

> **If you arrived via `/claude-api prompt-audit`:** this is the right file. Execute the steps below in order - do not summarize them back to the user. Start with Step 0 (establish scope and target model), and finish by producing both deliverables: the audit report (Step 5) and the proposed diff (Step 6).

Prompts, skills, and tool descriptions accumulate instructions tuned to older models: emphasis added because an old model under-triggered, step-by-step scripts added because an old model planned poorly, format scaffolds written before the API had structured outputs. Current Claude models follow instructions more closely and more literally than the models much of this text was written for, so the leftover text is not just wasted tokens - specific outdated instructions actively degrade behavior (over-triggering, over-planning, rigid responses in gray areas), while merely irrelevant text is comparatively harmless. The audit's job is therefore to find **specific dated instructions**, not to make prompts shorter. "Every token earns its place" is the frame; "make it short" is not.

**The audit produces two artifacts - both, always:**

1. **An audit report**: every finding with its location (`file:line`), the pattern it matches, why it is obsolete for the target model, and a confidence level.
2. **A proposed diff**: concrete edits for the findings that warrant them. Propose - never apply edits without the user's consent.

**Prime directive: distinguish cruft from load-bearing content.** A finding you cannot tie to a
</source-excerpt>

## 4. Desert Rose
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/theme-factory/themes/desert-rose.md`
- sha256: `bd065b8629be3b64655183927e248e3d892a27b8d184b009cfba89c96102744f`

<source-excerpt>
# Desert Rose

A soft and sophisticated theme with dusty, muted tones perfect for elegant presentations.

## Color Palette

- **Dusty Rose**: `#d4a5a5` - Soft primary color
- **Clay**: `#b87d6d` - Earthy accent
- **Sand**: `#e8d5c4` - Warm neutral backgrounds
- **Deep Burgundy**: `#5d2e46` - Rich dark contrast

## Typography

- **Headers**: FreeSans Bold
- **Body Text**: FreeSans

## Best Used For

Fashion presentations, beauty brands, wedding planning, interior design, boutique businesses.
</source-excerpt>

## 5. Agentic Retrieval with Knowledge Bases
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-sdk-python/skills/azure-search-documents-py/references/agentic-retrieval.md`
- sha256: `50754c0952a6e3dff537ecd0990636188679a282758931aea5e83bcdec429bd2`

<source-excerpt>
# Agentic Retrieval with Knowledge Bases

Agentic retrieval integrates an LLM to process queries, retrieve content, and generate grounded answers.

## Architecture

~~~
Knowledge Base (wraps LLM + sources)
    ├── Knowledge Source 1 → Search Index A
    ├── Knowledge Source 2 → Search Index B
    └── Azure OpenAI Model (query planning + answer synthesis)
~~~

## Setup Workflow

### 1. Create Index with Semantic Configuration

~~~python
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, VectorSearch, VectorSearchProfile,
    HnswAlgorithmConfiguration, AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters, SemanticSearch,
    SemanticConfiguration, SemanticPrioritizedFields, SemanticField
)

index = SearchIndex(
    name="my-index",
    fields=[
        SearchField(name="id", type="Edm.String", key=True, filterable=True),
        SearchField(name="content", type="Edm.String", filterable=False),
        SearchField(name="embedding", type="Collection(Edm.Single)",
                   stored=False, vector_search_dimensions=3072,
                   vector_search_profile_name="hnsw-profile"),
        SearchField(name="category", type="Edm.String", filterable=True, facetable=True)
    ],
    vector_search=VectorSearch(
        profiles=[VectorSearchProfile(
            name="hnsw-profile",
            algorithm_configuration_name="hnsw-algo",
            vectorizer_name="aoai-vectorizer"
        )],
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo")],
        vectorizers=[
</source-excerpt>

## 6. azure-app-onboard-prereq
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

## 7. azure-enterprise-infra-planner
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-enterprise-infra-planner/SKILL.md`
- sha256: `7e1b932f780b6348745b9d283437b64fc031ba452e8982ed9705849b9c19f50e`

<source-excerpt>
---
name: azure-enterprise-infra-planner
description: "Architect and provision enterprise Azure infrastructure from workload descriptions. For cloud architects and platform engineers planning networking, identity, security, compliance, and multi-resource topologies with WAF alignment. Generates Bicep or Terraform directly (no azd). WHEN: 'plan Azure infrastructure', 'architect Azure landing zone', 'design hub-spoke network', 'plan multi-region DR topology', 'set up VNets firewalls and private endpoints', 'subscription-scope Bicep deployment', 'Azure Backup for VM workloads'. PREFER azure-prepare FOR app-centric workflows."
license: MIT
metadata:
  author: Microsoft
  version: "1.4.1"
---

# Azure Enterprise Infra Planner

## When to Use This Skill

Activate this skill when user wants to:
- Plan enterprise Azure infrastructure from a workload or architecture description
- Architect a landing zone, hub-spoke network, or multi-region topology
- Design networking infrastructure: VNets, subnets, firewalls, private endpoints, VPN gateways
- Plan identity, RBAC, and compliance-driven infrastructure
- Generate Bicep or Terraform for subscription-scope or multi-resource-group deployments
- Plan disaster recovery, failover, or cross-region high-availability topologies

## Quick Reference

| Property | Details |
|---|---|
| MCP tools | `insights_get`, `get_azure_bestpractices_get`, `wellarchitectedframework_serviceguide_get`, `microsoft_docs_fetch`, `microsoft_docs_search`, `bicepschema_get` |
| CLI commands | `az deployment group create`, `az bicep build`, `az resource list`, `terraf
</source-excerpt>

## 8. azure-kubernetes
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-kubernetes/SKILL.md`
- sha256: `a5d09eecf5af6dd2a03397689c37aed69c4fef7965b3ff559878f2238a9464b5`

<source-excerpt>
---
name: azure-kubernetes
license: MIT
metadata:
  author: Microsoft
  version: "1.2.2"
description: "Plan, create, and configure production-ready Azure Kubernetes Service (AKS) clusters. Covers Day-0 checklist, SKU selection (Automatic vs Standard), networking options (private API server, Azure CNI Overlay, egress configuration), security, and operations (autoscaling, upgrade strategy, cost analysis). WHEN: create AKS environment, provision AKS, enable AKS observability, design AKS networking, choose AKS SKU, secure AKS, optimize AKS, AKS spot nodes, AKS cluster-autoscaler, rightsize AKS pod, pod rightsizing, over-provisioned AKS pod, pod resource requests and limits, Vertical Pod Autoscaler, VPA recommendations."
---

# Azure Kubernetes Service

> **AUTHORITATIVE GUIDANCE — MANDATORY COMPLIANCE**
>
> This skill produces a **recommended AKS cluster configuration** based on user requirements, distinguishing **Day-0 decisions** (networking, API server — hard to change later) from **Day-1 features** (can enable post-creation). See [CLI reference](./references/cli-reference.md) for commands.

## Quick Reference
| Property | Value |
|----------|-------|
| Best for | AKS cluster planning and Day-0 decisions |
| MCP Tools | `mcp_azure_mcp_aks` |
| CLI | `az aks create`, `az aks show`, `kubectl get`, `kubectl describe` |
| Related skills | azure-kubernetes-app-deploy (deploy an app to an existing cluster), azure-diagnostics (troubleshooting AKS), azure-validate (readiness checks), azure-kubernetes-automatic-readiness (migrate existing cluster to AKS Automatic) |

## When to Use T
</source-excerpt>
