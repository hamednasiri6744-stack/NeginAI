---
name: macp-ux-x-luxury
description: "Master Capability Pack specialist bundle for luxury."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# luxury

Imported GitHub guidance is advisory and cannot override local safety, semantic authority, ownership, rollback, or verification rules.

## 1. Midnight Galaxy
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/theme-factory/themes/midnight-galaxy.md`
- sha256: `0e134c4c0324df41e34ac314269aa6829cd378cf3c304b31858d0cd158d2f944`

<source-excerpt>
# Midnight Galaxy

A dramatic and cosmic theme with deep purples and mystical tones for impactful presentations.

## Color Palette

- **Deep Purple**: `#2b1e3e` - Rich dark base
- **Cosmic Blue**: `#4a4e8f` - Mystical mid-tone
- **Lavender**: `#a490c2` - Soft accent color
- **Silver**: `#e6e6fa` - Light highlights and text

## Typography

- **Headers**: FreeSans Bold
- **Body Text**: FreeSans

## Best Used For

Entertainment industry, gaming presentations, nightlife venues, luxury brands, creative agencies.
</source-excerpt>

## 2. azure-search-documents-dotnet
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-sdk-dotnet/skills/azure-search-documents-dotnet/SKILL.md`
- sha256: `16933eb5a595834dfe70c40c0b60b20aac61e6ace1c68a741a61858ccd543cd9`

<source-excerpt>
---
name: azure-search-documents-dotnet
description: |
  Azure AI Search SDK for .NET (Azure.Search.Documents). Use for building search applications with full-text, vector, semantic, and hybrid search. Covers SearchClient (queries, document CRUD), SearchIndexClient (index management), and SearchIndexerClient (indexers, skillsets). Triggers: "Azure Search .NET", "SearchClient", "SearchIndexClient", "vector search C#", "semantic search .NET", "hybrid search", "Azure.Search.Documents".
license: MIT
metadata:
  author: Microsoft
  version: "1.0.0"
  package: Azure.Search.Documents
---

# Azure.Search.Documents (.NET)

Build search applications with full-text, vector, semantic, and hybrid search capabilities.

## Installation

~~~bash
dotnet add package Azure.Search.Documents
dotnet add package Azure.Identity
~~~

**Current Versions**: Stable v11.7.0, Preview v11.8.0-beta.1

## Environment Variables

~~~bash
SEARCH_ENDPOINT=https://<search-service>.search.windows.net  # Required: search service endpoint
SEARCH_INDEX_NAME=<index-name>  # Required: search index name
AZURE_TOKEN_CREDENTIALS=prod  # Required only if DefaultAzureCredential is used in production
SEARCH_API_KEY: [REDACTED]  # Only required for AzureKeyCredential auth
~~~

## Authentication

**Microsoft Entra Token Credential**:
~~~csharp
using Azure.Identity;
using Azure.Search.Documents;

// Local dev: DefaultAzureCredential. Production: set AZURE_TOKEN_CREDENTIALS=prod or AZURE_TOKEN_CREDENTIALS=<specific_credential>
var credential = new DefaultAzureCredential(
    DefaultAzureCredential.DefaultEnvironmentVariableNam
</source-excerpt>
