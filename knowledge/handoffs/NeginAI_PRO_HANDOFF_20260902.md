# START HERE — NeginAI Pro Project Handoff

این سند را می‌توان به‌تنهایی به Agent اکانت Pro داد.

## Mission

NeginAI را به یک **Enterprise Operational & AI Platform** استاندارد، سریع، امن و قابل‌توسعه تبدیل کن؛ بدون از دست‌دادن قابلیت‌های فعلی و بدون تقلیل پروژه به یک chatbot.

## USER-CONFIRMED DECISIONS

- NeginAI محصول رسمی و جامع سازمان است.
- اپ سفارش‌گذاری ویزیتور و Seller workflow از حیاتی‌ترین قسمت‌های محصول‌اند.
- UI/تجربه AI باید داخل خود NeginAI باشد؛ کاربر نباید به ChatGPT یا اپ خارجی منتقل شود.
- Local LLM / local inference در معماری هدف مجاز نیست.
- جهت مطلوب AI: **نرم‌افزار بسیار قوی + مدل ابری بسیار ارزان**؛ ترجیح provider ایرانی فقط در صورتی که benchmark، reliability، privacy و tool/structured-output requirements را پاس کند.

## Current system — FACTS from 2026-09-01 forensic snapshot

- Python 3.11 / FastAPI backend, approximately 19 routers.
- Web UI: static HTML/CSS/JS under `app/static`.
- PWA-like service worker / web capabilities exist, but frontend is not a modern TypeScript application framework.
- Android SellerNavigator: Kotlin/Jetpack Compose + WebView/native integrations; active/testing.
- iOS SellerNavigator: experimental prototype.
- SQLite stores application state; SQL Server/Varanegar provides ERP read data.
- Guarded Varanegar ReadWrite order bridge exists and is safety-critical.
- OpenAI integration currently powers chat/attachments/audio/automation.
- Neshan and NGT are additional external integrations.
- Canonical Git repository for the active application was not proven in the forensic snapshot.
- Snapshot launch status: NO-GO due to unresolved release identity, security, authorization, runtime parity, regression, observability and order reliability evidence.

## Final recommended architecture

### 1. Keep the product, change the AI dependency model

NeginAI owns:
- UI/PWA/mobile experience
- Identity/RBAC
- Business semantics
- Skills and tools
- MCP capability surface where useful
- SQL/ERP access
- Analytics/calculations
- Forecasting/optimization
- Memory/RAG
- Verification/guardrails
- Audit/approval
- Provider routing

LLM provider owns only:
- language understanding
- constrained planning/classification when deterministic routing is insufficient
- synthesis/explanation
- limited reasoning over a compact evidence package

### 2. Do not ask the cheap model to solve the whole problem

For a complex question, use:

```text
User question
 -> intent normalization
 -> task decomposition
 -> deterministic skill/tool selection where possible
 -> parallel data/analytics execution
 -> evidence reconciliation
 -> compact evidence package
 -> cheap LLM synthesis
 -> factual/business verifier
 -> answer
```

### 3. Provider-agnostic AI Gateway

Never scatter provider SDK calls through business services. All inference must pass through one internal contract, e.g.:

```text
AI.chat()
AI.classify()
AI.structured_generate(schema)
AI.summarize(evidence)
AI.transcribe()       # if the chosen provider supports it
AI.embed()            # if required
```

Implement provider adapters behind this contract. Provider choice is **OPEN DECISION** until benchmarked.

### 4. MCP is not the model

Use MCP to standardize capabilities/tools if it improves reuse across agents/clients. Do **not** treat MCP as a way to convert a ChatGPT subscription into a free backend API. Inference still needs an approved provider.

### 5. Frontend modernization

**RECOMMENDATION:** preserve FastAPI/domain services and incrementally modernize `app/static` to React + TypeScript + Vite PWA. No big-bang rewrite. Keep Android native capabilities until equivalent behavior is proven.

### 6. Safety boundary

LLM must never directly:
- execute arbitrary SQL,
- write ERP orders,
- bypass RBAC,
- invent business facts,
- perform irreversible actions without a typed tool, authorization and audit.

### 7. Quality strategy

Create an NeginAI benchmark from real organizational questions. Select the **cheapest provider/model that passes the quality gate**, not the most famous model.

Required dimensions:
- Persian intent accuracy
- tool/skill selection
- structured JSON/schema compliance
- complex multi-step enterprise question accuracy
- factuality against verified ERP evidence
- hallucination rate
- latency p50/p95
- reliability/rate-limit behavior
- privacy/data-retention terms
- cost per successful enterprise task

## Non-negotiable implementation rule

**Do not report a feature COMPLETE without verification evidence.** Order write/reconcile, auth, source provenance, rollback, deployment, PWA offline behavior, Android behavior and AI factuality each require explicit postconditions.

## Critical path

NOW: establish canonical source/release identity and protect critical seller/order path.  
NEXT: introduce AI Gateway + semantic/tool/evidence layers and benchmark cheap providers.  
LATER: incremental frontend/PWA modernization and optional iOS productionization.
