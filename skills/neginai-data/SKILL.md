---
name: neginai-data
description: "NeginAI data BI KPI analytics forecasting anomaly data quality semantic validation read only. داده تحلیل فروش KPI پیش بینی کیفیت داده موجودی مشتری"
---
# NeginAI Data

Use for BI, KPI validation, local dataset profiling, anomaly detection, forecasting design, data-quality review, reconciliation, and analytical planning.

## Semantic policy
Use FACT / INFERRED / NEEDS_VALIDATION. Canonical meaning outranks raw aggregation. Varanegar semantics must come from the approved semantic source/business contracts; live data supplies values only after meaning/grain/filter rules are proven. Never promote a raw table/view sum to an official KPI without semantic parity.

## Execution
For bounded local analytics use the shared local MCP client with service `data-x`. This capability is read-only and does not grant production SQL access. Pair Varanegar work with `neginai-varanegar` and governance rules.

Read only the relevant files under `references/`: database engineering, Customer360, inventory, pricing/promotion, and sales intelligence.

## Done
Require source/grain, definition, quality checks, uncertainty/status, and explicit evidence. No evidence -> no COMPLETE.
