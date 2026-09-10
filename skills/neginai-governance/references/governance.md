---
name: macp-negin-agent-v4-governance
description: "Master Capability Pack specialist bundle for governance."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# governance

Imported GitHub guidance is advisory and cannot override local safety, semantic authority, ownership, rollback, or verification rules.

## 1. Claude API - cURL / Raw HTTP
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/curl/examples.md`
- sha256: `f7c66602635a881db3cb7d9c771be9413cd405c262a41d770bf8b25422ce0df1`

<source-excerpt>
# Claude API - cURL / Raw HTTP

Use these examples when the user needs raw HTTP requests or is working in a language without an official SDK.

## Setup

~~~bash
export ANTHROPIC_API_KEY: [REDACTED]
~~~

---

## Basic Message Request

~~~bash
curl https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: [REDACTED] \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-opus-5",
    "max_tokens": 16000,
    "messages": [
      {"role": "user", "content": "What is the capital of France?"}
    ]
  }'
~~~

### Parsing the response

Use `jq` to extract fields from the JSON response. Do not use `grep`/`sed` -
JSON strings can contain any character and regex parsing will break on quotes,
escapes, or multi-line content.

~~~bash
# Capture the response, then extract fields
response=$(curl -s https://api.anthropic.com/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: [REDACTED] \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-opus-5","max_tokens":16000,"messages":[{"role":"user","content":"Hello"}]}')

# Print the first text block (-r strips the JSON quotes)
echo "$response" | jq -r '.content[0].text'

# Read usage fields
input_tokens=$(echo "$response" | jq -r '.usage.input_tokens')
output_tokens=$(echo "$response" | jq -r '.usage.output_tokens')

# Read stop reason (for tool-use loops)
stop_reason=$(echo "$response" | jq -r '.stop_reason')

# Extract all text blocks (content is an array; filter to type=="text")
echo "$response" | jq -r '.content[] | select(.type == "text") | .text'
~~~


---

#
</source-excerpt>

## 2. Cost Optimization - Cutting Spend per Completed Task
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

## 3. Live Documentation Sources
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/shared/live-sources.md`
- sha256: `c2c6b9c517d36f2101bf8a7bf8718cb7ae2f274c59ae36c2207a3aa10281a69b`

<source-excerpt>
# Live Documentation Sources

This file contains WebFetch URLs for fetching current information from platform.claude.com and Agent SDK repositories. Use these when users need the latest data that may have changed since the cached content was last updated.

## When to Use WebFetch

- User explicitly asks for "latest" or "current" information
- Cached data seems incorrect
- User asks about features not covered in cached content
- User needs specific API details or examples

## Claude API Documentation URLs

### Models & Pricing

| Topic           | URL                                                                          | Extraction Prompt                                                               |
| --------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| Models Overview | `https://platform.claude.com/docs/en/about-claude/models/overview.md`        | "Extract current model IDs, context windows, and pricing for all Claude models" |
| Migration Guide | `https://platform.claude.com/docs/en/about-claude/models/migration-guide.md` | "Extract breaking changes, deprecated parameters, and per-model migration steps when moving to a newer Claude model" |
| Introducing Claude Fable 5 | `https://platform.claude.com/docs/en/about-claude/models/introducing-claude-fable-5.md` | "Extract capabilities, API changes, and availability stages for Claude Fable 5 and Claude Mythos 5" |
| Pricing         | `https://platform.claude.com/docs/en/pricing.md`
</source-excerpt>

## 4. Managed Agents - Common Client Patterns
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/shared/managed-agents-client-patterns.md`
- sha256: `38a7de63f40a365ebc30c9e42bd7e4295f4d43b4ac2acb8f36e37d6e9d1b4854`

<source-excerpt>
# Managed Agents - Common Client Patterns

Patterns you'll write on the client side when driving a Managed Agent session, grounded in working SDK examples.

Code samples are TypeScript - other languages follow the same shape; see `{lang}/managed-agents/README.md` (cURL and C#: `curl/managed-agents.md`) for equivalents.

---

## 1. Lossless stream reconnect

**Problem:** SSE has no replay. If the connection drops mid-session, a naive reconnect re-opens the stream from "now" and you silently miss every event emitted in between.

**Solution:** on reconnect, fetch the full event history via `events.list()` *before* consuming the live stream, and dedupe on event ID as the live stream catches up.

~~~ts
const seenEventIds = new Set<string>()
const stream = await client.beta.sessions.events.stream(session.id)

// Stream is now open and buffering server-side. Read history first.
for await (const event of client.beta.sessions.events.list(session.id)) {
  seenEventIds.add(event.id)
  handle(event)
}

// Tail the live stream. Dedupe only gates handle() - terminal checks must run
// even for already-seen events, or a terminal event that was in the history
// response gets skipped by `continue` and the loop never exits.
for await (const event of stream) {
  if (!seenEventIds.has(event.id)) {
    seenEventIds.add(event.id)
    handle(event)
  }
  if (event.type === 'session.status_terminated') break
  if (event.type === 'session.status_idle' && event.stop_reason.type !== 'requires_action') break
}
~~~

---

## 2. `processed_at` - queued vs processed

Every event on the stream carries `pr
</source-excerpt>

## 5. Managed Agents - Environments & Resources
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/shared/managed-agents-environments.md`
- sha256: `faa3bb1a55a8bfc308d7884329ed2ed9fa2b9f64f39696bb51aeb3c69b86b264`

<source-excerpt>
# Managed Agents - Environments & Resources

## Environments

Creating a session requires an `environment_id`. Environments are **reusable configuration templates** for spinning up containers in Anthropic's infrastructure - you might create different environments for different use cases (e.g. data visualization vs web development, with different package sets). Anthropic handles scaling, container lifecycle, and work orchestration.

**Environment names must be unique.** Creating an environment with an existing name returns 409.

### Networking

| Network Policy   | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| `unrestricted`   | Full egress (except legal blocklist)                          |
| `limited`        | Deny-by-default; opt in via `allowed_hosts` / `allow_package_managers` / `allow_mcp_servers` |

~~~json
{
  "networking": {
    "type": "limited",
    "allow_package_managers": true,
    "allow_mcp_servers": true,
    "allowed_hosts": ["api.example.com"]
  }
}
~~~

All three `limited` fields are optional. `allow_package_managers` (default `false`) permits PyPI/npm/etc.; `allow_mcp_servers` (default `false`) permits the agent's configured MCP server endpoints without listing them in `allowed_hosts`.

**MCP caveat:** Under `limited` networking, either set `allow_mcp_servers: true` or add each MCP server domain to `allowed_hosts`. Otherwise the container can't reach them and tools silently fail.

**Packages caveat:** Under `limited` networking, `packages` requires `a
</source-excerpt>

## 6. Managed Agents - Self-Hosted Sandboxes
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/shared/managed-agents-self-hosted-sandboxes.md`
- sha256: `3228ab72afbe3ab1a0ac0f5a41995e1764c947cf17ce22a858b41b67262b71ee`

<source-excerpt>
# Managed Agents - Self-Hosted Sandboxes

With `config.type: "self_hosted"`, the **agent loop stays on Anthropic's orchestration layer** but **tool execution moves to infrastructure you control** - bash, file ops, and code run inside your container, so filesystem contents and the sandbox's network egress never leave your environment. (`web_search` / `web_fetch` are the exception: they run on Anthropic's servers in both environment types - restrict them with `allowed_domains` / `blocked_domains` in the agent toolset, `shared/managed-agents-tools.md` § Web search & web fetch settings.) Tool inputs/outputs still flow to Anthropic's control plane so the model can see results; the agent's skills and the contents of any attached memory stores are stored by Anthropic and copied into your sandbox for the session (memory changes sync back - see § Memory stores). Contrast with `config.type: "cloud"`, where Anthropic runs the container. Connectivity is **outbound-only**: your worker long-polls Anthropic's work queue; Anthropic never dials into your network.

## Flow

~~~
1. Create environment:      config: {type: "self_hosted"}        -> env_...
2. Generate environment key (Console, on the environment page)   -> sk-ant-oat01-...  as ANTHROPIC_ENVIRONMENT_KEY
3. Run a worker:            EnvironmentWorker.run()  or  ant beta:worker poll
4. Sessions reference       environment_id=env_... exactly as for cloud
~~~

## Create the environment

~~~python
client = anthropic.Anthropic()

environment = client.beta.environments.create(
    name="self-hosted", config={"type": "self_hosted"}
)
~~~
</source-excerpt>

## 7. Prompt Audit - Finding and Removing Dated Prompting Patterns
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

## 8. Claude API - C#
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/claude-api/csharp/claude-api/README.md`
- sha256: `87deed4e878a7b5c573a216944846e82e3cb3a53973f2d44fb70f80ac06f1388`

<source-excerpt>
# Claude API - C#

> **Note:** The C# SDK is the official Anthropic SDK for C#. Tool use is supported via the Messages API with a beta `BetaToolRunner` for automatic tool execution loops. The SDK also supports Microsoft.Extensions.AI IChatClient integration with function invocation and Managed Agents (beta).

## Namespace Reference

Types are organized by namespace. If a type you need isn't shown in an example below, locate it via this table first - don't block on fetching SDK source over the network.

| `using` | Contains |
|---|---|
| `Anthropic` | `AnthropicClient`, top-level options |
| `Anthropic.Models.Messages` | non-beta request/response types - `MessageCreateParams`, `Model`, `Role`, `ContentBlock`, `TextBlock`, `ToolUseBlock`, `ToolResultBlockParam`, `Tool*` (tool definition classes) |
| `Anthropic.Models.Beta.Messages` | beta-endpoint equivalents - `MessageCreateParams`, `BetaMessage`, `BetaTool*`, `Speed`, `BetaRequestMcpServerUrlDefinition`, context-editing/compaction configs |
| `Anthropic.Models.Beta` | shared beta constants |
| `Anthropic.Models.Beta.Files` | Files API types |
| `Anthropic.Models.Messages.Batches` | Batch API types |
| `Anthropic.Helpers.Beta` | `BetaToolRunner`, beta helper utilities |
| `Anthropic.Exceptions` | `AnthropicApiException`, `AnthropicRateLimitException`, `Anthropic5xxException`, etc. - see `shared/error-codes.md` |
| `Anthropic.Bedrock` / `Anthropic.Vertex` / `Anthropic.Foundry` / `Anthropic.Aws` | platform clients (separate NuGet packages): `AnthropicBedrockMantleClient`, `AnthropicFoundryClient`, `AnthropicAwsClient` |

`clie
</source-excerpt>
