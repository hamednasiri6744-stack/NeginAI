---
name: neginai-shell-ops
description: "NeginAI Windows shell PowerShell CMD remote execution timeout process service MCP Cloudflare diagnostics reliability recovery. شل پاورشل ویندوز رموت تيم اوت سرویس ع͸Ȩ يابی"
"license: MIT
---

# NeginAI Shell Operations

Use this skill for Windows shell, PowerShell, CMD, remote execution, long-running commands, service diagnostics, MCP/agent process checks, Cloudflare tunnel checks, and timeout-prone operational tasks.

## Operating model

1. Classify the command before execution: quick probe, filesystem inspection, network/service check, build/test, or long-running process.
2. Prefer PowerShell for Windows-native inspection and structured output. Use `cmd /c` only for commands that specifically require CMD semantics.
3. Run a cheap preflight before an expensive command: verify path, executable, service, port, and required environment are present.
4. Set an explicit timeout budget per step. Do not reuse a short probe timeout for a build, package install, tunnel startup, or integration test.
5. Split independent checks into separate steps so one slow operation does not hide all other evidence.
6. When a tool supports persistent processes, start the process once and poll/read its output instead of repeatedly launching the same command.
7. Treat timeout as an unknown state, not automatic failure. Check whether the process is still running and whether useful output or side effects occurred before retrying.
8. On retry, change one variable at a time: timeout, shell, working directory, argument quoting, or execution mode. Never create uncontrolled retry loops.
9. Capture exit code, stdout, stderr, elapsed time, and the exact failing step before declaring a root cause.
10. Finish with the narrowest verification that proves the requested outcome.

## Timeout policy

- Quick local probes should normally complete in seconds.
- Service, network, package, and MCP checks may need tens of seconds.
- Builds, installs, indexing, or integration tests may need minutes.
- Use the highest timeout permitted by the active tool only when the operation justifies it.
- If a command is expected to remain alive, use a persistent/background execution primitive when available instead of waiting for process exit.

## Windows reliability rules

- Quote paths containing spaces and prefer absolute paths when working across drives.
- Set the working directory explicitly before project commands.
- Verify whether the active shell is PowerShell, CMD, or another runtime before using shell-specific syntax.
- For services, check status before restart or termination.
- For ports, identify the owning process before any kill action.
- For Cloudflare/MCP/agent diagnostics, separate local health, listener/port state, tunnel state, and external reachability into distinct checks.
- Do not infer that HTTP 401/403/404 means a service is down; interpret it in the context of the expected endpoint and authentication boundary.

## Guardrails

- Prefer read-only diagnostics first.
- Never expose passwords, API keys, tokens, cookies, private keys, or connection strings.
- Do not perform destructive filesystem, database, registry, boot, firewall, or service changes without explicit owner authorization.
- Do not kill a process merely because a command timed out; first prove that it is the intended target and that termination is safe.
- Preserve unrelated running services and user work.
- For Varanegar/ERP databases, SQL access remains read-only.

## Completion evidence

A shell/remote task is COMPLETE only when the requested postcondition is directly verified. A successful command launch is not enough. Report the final state, the evidence used, and any remaining uncertainty.
