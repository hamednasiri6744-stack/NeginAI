---
name: macp-negin-agent-v4-workflows
description: "Master Capability Pack specialist bundle for workflows."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# workflows

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

## 2. Update Foundry llms.txt Documentation
- source: `microsoft-skills@02e0b2f852b3`
- kind: `workflow`
- raw: `raw/microsoft-skills/.github/workflows/update-llms-txt.md`
- sha256: `448b39e52b72df781e9a2965e1a4e18e1a7ced6ec75af82806bf83ee71b072ac`

<source-excerpt>
---
on:
  schedule: "0 3 * * *"  # 7 PM PST (3 AM UTC) daily
  workflow_dispatch:
permissions:
  contents: read
  issues: read
  pull-requests: read
network:
  allowed:
    - defaults
    - learn.microsoft.com
    - pypi.org
    - files.pythonhosted.org
tools:
  github:
  bash: ["python3", "pip", "git", "diff"]
safe-outputs:
  create-pull-request:
    title-prefix: "[docs-update] "
    labels: [automated, documentation]
---

# Update Foundry llms.txt Documentation

Regenerate the llms.txt and llms-full.txt files from the latest Microsoft Foundry documentation.

## Purpose

This workflow keeps our Foundry documentation index up-to-date by:
1. Fetching the latest Table of Contents from Microsoft Learn
2. Regenerating llms.txt with current documentation links
3. Creating a PR if there are changes

## Steps

1. **Setup Python environment**
   - Install required packages: `pip install aiohttp`

2. **Run the scraper**
   - Execute `python .github/scripts/scrape_foundry_docs.py` to regenerate llms.txt
   - Execute `python .github/scripts/generate_llms_full.py` to regenerate llms-full.txt

3. **Check for changes**
   - Compare the generated files with the existing ones
   - If there are changes, create a pull request with the updates

4. **Create PR if needed**
   - Title: "Update Foundry llms.txt documentation"
   - Include summary of what changed (new pages, removed pages, section changes)

## Notes

- The scraper respects rate limits when fetching from Microsoft Learn
- Only creates a PR if there are actual content changes
- The llms.txt follows the llms.txt specification for LL
</source-excerpt>

## 3. azure-ai-contentunderstanding-py
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-sdk-python/skills/azure-ai-contentunderstanding-py/SKILL.md`
- sha256: `3bb3d811f73db5724d3d64d572819a43467803e3e15ce20024845e9bb0a534a7`

<source-excerpt>
---
name: azure-ai-contentunderstanding-py
description: |
  Azure AI Content Understanding SDK for Python. Use for multimodal content extraction from documents, images, audio, and video.
  Triggers: "azure-ai-contentunderstanding", "ContentUnderstandingClient", "multimodal analysis", "document extraction", "video analysis", "audio transcription".
license: MIT
metadata:
  author: Microsoft
  version: "1.0.0"
  package: azure-ai-contentunderstanding
---

# Azure AI Content Understanding SDK for Python

Multimodal AI service that extracts semantic content from documents, video, audio, and image files for RAG and automated workflows.

## Installation

~~~bash
pip install azure-ai-contentunderstanding
~~~

## Environment Variables

~~~bash
CONTENTUNDERSTANDING_ENDPOINT=https://<resource>.cognitiveservices.azure.com/  # Required for all auth methods
AZURE_TOKEN_CREDENTIALS=prod # Required only if DefaultAzureCredential is used in production
~~~

## Authentication & Lifecycle

> **🔑 Two rules apply to every code sample below:**
>
> 1. **Prefer `DefaultAzureCredential`.** It works locally (Azure CLI / VS Code / Developer CLI) and in Azure (managed identity, workload identity) with no code change. Avoid connection strings, account/API keys — they bypass Entra audit and rotation.
>    - Local dev: `DefaultAzureCredential` works as-is.
>    - Production: set `AZURE_TOKEN_CREDENTIALS=prod` (or `AZURE_TOKEN_CREDENTIALS=<specific_credential>`) to constrain the credential chain to production-safe credentials.
> 2. **Wrap every client in a context manager** so HTTP transports, sockets, and
</source-excerpt>

## 4. Keys Reference
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-sdk-typescript/skills/azure-keyvault-keys-ts/references/keys.md`
- sha256: `cb436dc541fc0dbf94848066888cfac9ef368cf25887a20c19220a8bc9eec548`

<source-excerpt>
# Keys Reference

Cryptographic key management and operations using @azure/keyvault-keys SDK.

## Overview

The Key Vault Keys SDK provides two main clients:
- **KeyClient** - CRUD operations for keys (create, get, list, rotate, delete)
- **CryptographyClient** - Cryptographic operations using keys (encrypt, decrypt, sign, verify, wrap, unwrap)

## Core Types

~~~typescript
import {
  KeyClient,
  CryptographyClient,
  KeyVaultKey,
  KeyProperties,
  DeletedKey,
  KeyRotationPolicy,
  KeyRotationPolicyProperties,
  KeyRotationLifetimeAction,
  CreateKeyOptions,
  CreateRsaKeyOptions,
  CreateEcKeyOptions,
  EncryptParameters,
  DecryptParameters,
  SignResult,
  VerifyResult,
  WrapResult,
  UnwrapResult,
  KnownEncryptionAlgorithms,
  KnownSignatureAlgorithms,
  KnownKeyTypes,
  KnownKeyCurveNames
} from "@azure/keyvault-keys";
~~~

## KeyClient Initialization

~~~typescript
import { KeyClient } from "@azure/keyvault-keys";
import { DefaultAzureCredential } from "@azure/identity";

const vaultUrl = `https://${process.env.AZURE_KEYVAULT_NAME}.vault.azure.net`;
const credential = new DefaultAzureCredential();

const keyClient = new KeyClient(vaultUrl, credential);
~~~

## Creating Keys

### RSA Keys

~~~typescript
// Basic RSA key (default 2048-bit)
const rsaKey = await keyClient.createRsaKey("my-rsa-key");

// RSA key with specific size
const rsaKey2048 = await keyClient.createRsaKey("my-rsa-2048", {
  keySize: 2048
});

const rsaKey4096 = await keyClient.createRsaKey("my-rsa-4096", {
  keySize: 4096
});

// RSA-HSM (Hardware Security Module backed)
const rsaHsmKey = await
</source-excerpt>

## 5. azure-upgrade
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-upgrade/SKILL.md`
- sha256: `26b538372a248f42a6c1976eb307c19ae3f6966a1bcbe7a066b4090f9568d6ab`

<source-excerpt>
---
name: azure-upgrade
description: "Assess and upgrade Azure workloads between plans, tiers, or SKUs, or modernize Azure SDK dependencies in source code. WHEN: upgrade Consumption to Flex Consumption, upgrade Azure Functions plan, change hosting plan, function app SKU, migrate App Service to Container Apps, modernize legacy Azure Java SDKs (com.microsoft.azure to com.azure), migrate Azure Cache for Redis (ACR/ACRE) to Azure Managed Redis (AMR)."
license: MIT
compatibility: python3.10+
metadata:
  author: Microsoft
  version: "1.2.1"
---

# Azure Upgrade

> This skill handles **assessment and automated upgrades** of existing Azure workloads from one Azure service, hosting plan, or SKU to another — all within Azure. This includes plan/tier upgrades (e.g. Consumption → Flex Consumption), cross-service migrations (e.g. App Service → Container Apps), and SKU changes. It also covers **Azure SDK for Java source-code modernization** (e.g. legacy Java `com.microsoft.azure.*` → modern `com.azure.*`). This is NOT for cross-cloud migration — use `azure-cloud-migrate` for that.

## Triggers

| User Intent | Example Prompts |
|-------------|-----------------|
| Upgrade Azure Functions plan | "Upgrade my function app from Consumption to Flex Consumption" |
| Change hosting tier | "Move my function app to a better plan" |
| Assess upgrade readiness | "Is my function app ready for Flex Consumption?" |
| Automate plan migration | "Automate the steps to upgrade my Functions plan" |
| Modernize legacy Azure Java SDK | "Migrate legacy Azure SDKs for Java", "Upgrade legacy Azure Java SDK", "Mi
</source-excerpt>

## 6. Key Vault Expiration Audit & Compliance
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-compliance/references/azure-keyvault-expiration-audit.md`
- sha256: `6e372fef0dcb1d717d9c34802140273057446d2748e267334468b0cd7c3adae6`

<source-excerpt>
# Key Vault Expiration Audit & Compliance

Automated auditing of Azure Key Vault resources to identify expired or expiring keys, secrets, and certificates before they cause service disruptions.

## Overview

This skill monitors Azure Key Vault resources (keys, secrets, certificates) for expiration issues. It helps prevent service disruptions by identifying:
- **Expired resources** causing active problems
- **Expiring soon** (within customizable days threshold)
- **Missing expiration dates** (security risk)
- **Disabled resources** needing cleanup

## Core Workflow

1. **List Resources**: Enumerate keys, secrets, and certificates in target vault(s)
2. **Get Details**: Retrieve expiration metadata for each resource
3. **Analyze Status**: Compare expiration dates against current date and threshold
4. **Generate Report**: Organize findings by priority with actionable recommendations

## Audit Patterns

### Pattern 1: Single Vault Quick Scan
Check one Key Vault for all expiration issues with configurable day threshold (default: 30 days).

**Tools**: `keyvault_key_list`, `keyvault_key_get`, `keyvault_secret_list`, `keyvault_secret_get`, `keyvault_certificate_list`, `keyvault_certificate_get`

### Pattern 2: Multi-Vault Compliance Report
Scan multiple vaults across subscription for comprehensive security review.

**Use for**: Quarterly audits, organization-wide compliance checks

### Pattern 3: Resource Type Focus
Audit only keys, secrets, OR certificates when specific resource type is mentioned.

**Use for**: Certificate renewal planning, secret rotation tracking

### Pattern 4:
</source-excerpt>

## 7. CI/CD Deploy Recipe
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-deploy/references/recipes/cicd/README.md`
- sha256: `78f12e53c49480719dc1bb92a8d4142b4ebd7390da733b098f23c5c30b1a3a93`

<source-excerpt>
# CI/CD Deploy Recipe

Deploy to Azure using automated pipelines.

## Prerequisites

- `.azure/deployment-plan.md` exists with status `Validated`
- Azure Service Principal or federated credentials configured
- Pipeline file exists (`.github/workflows/` or `azure-pipelines.yml`)

## GitHub Actions

| Example | Description |
|---------|-------------|
| [github-azd.yml](examples/github-azd.yml) | AZD deployment workflow |
| [github-bicep.yml](examples/github-bicep.yml) | Bicep infrastructure deployment |

## Azure DevOps

| Example | Description |
|---------|-------------|
| [azdo-azd.yml](examples/azdo-azd.yml) | Basic AZD pipeline |
| [azdo-multistage.yml](examples/azdo-multistage.yml) | Multi-stage with approvals |

## Setup Requirements

### GitHub Actions

1. Create Azure Service Principal with federated credentials
2. Add secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
3. Add variables: `AZURE_ENV_NAME`, `AZURE_LOCATION`
4. Create environments with protection rules

### Azure DevOps

1. Create Service Connection to Azure
2. Create Variable Groups per environment
3. Create Environments with approval gates

## References

- [Verification steps](./verify.md)
- [Error handling](./errors.md)
</source-excerpt>

## 8. .NET Aspire Projects
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-prepare/references/aspire.md`
- sha256: `38be26f15252019e6ea479c6889b7c99f4a579ccfb1a4f9aa54cf8cb4dc13967`

<source-excerpt>
# .NET Aspire Projects

> ⛔ **CRITICAL - READ THIS FIRST**
>
> For .NET Aspire projects, **NEVER manually create azure.yaml or infra/ files.**
> Always use `azd init --from-code` which auto-detects the AppHost and generates everything correctly.
>
> **Failure to follow this causes:** "Could not find a part of the path 'infra\main.bicep'" error.

Guidance for preparing .NET Aspire applications for Azure deployment.

**📖 For detailed AZD workflow:** See [recipes/azd/aspire.md](recipes/azd/aspire.md)

## What is .NET Aspire?

.NET Aspire is an opinionated, cloud-ready stack for building observable, production-ready distributed applications. Aspire projects use an AppHost orchestrator to define and configure the application's components, services, and dependencies.

## Detection

A .NET Aspire project is identified by:

| Indicator | Description |
|-----------|-------------|
| `*.AppHost.csproj` | AppHost orchestrator project file |
| `Aspire.Hosting` package | Core Aspire hosting package reference |
| `Aspire.Hosting.AppHost` | Alternative Aspire hosting package |

**Example project structure:**
~~~
orleans-voting/
├── OrleansVoting.sln
├── OrleansVoting.AppHost/
│   └── OrleansVoting.AppHost.csproj   ← AppHost indicator
├── OrleansVoting.Web/
├── OrleansVoting.Api/
└── OrleansVoting.Grains/
~~~

## Azure Preparation Workflow

### Step 1: Detection

When scanning the codebase (per [scan.md](scan.md)), detect Aspire by:

~~~bash
# Check for AppHost project
find . -name "*.AppHost.csproj"

# Or check for Aspire.Hosting package reference
grep -r "Aspire.Hosting" . --include="*.cs
</source-excerpt>
