---
name: neginai-automation
description: "NeginAI automation n8n Airflow API webhook orchestration retry idempotency observability workflow. اتوماسیون وبهوک ایرفلو n8n ارکستریشن مانیتورینگ"
---
# NeginAI Automation

Use for n8n/Airflow architecture, API/webhook contracts, orchestration, retry/backoff, idempotency, compensation, failure handling, runbooks, and observability.

## Execution policy
Design and statically audit before mutation. Use the shared local MCP client with service `automation-x` for advisory/read-only workflow capabilities. It does not activate/update/delete n8n workflows or operate Airflow. Production side effects, credentials, remote changes, and destructive actions require the approved guarded boundary plus explicit owner authorization.

Read `references/orchestration.md` and `references/workflows.md` when relevant.

## Required properties
Stable idempotency key; bounded retry with retryable classes; timeout budget; failure/dead-letter route; correlation/run IDs; rollback or compensation; observable business outcome.

## Done
No workflow is COMPLETE until validation plus runtime evidence exists for the requested scope.
