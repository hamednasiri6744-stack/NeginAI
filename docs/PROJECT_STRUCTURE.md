# NeginAI Project Structure

This file defines the canonical repository layout. New files should follow this map so temporary work does not accumulate in the source tree.

## Canonical source

- `app/` — FastAPI backend and backend services.
- `vnext/` — canonical React/Vite frontend.
- `android/` — Android client/project.
- `ios/` — iOS client/project.
- `ops/` — production/runtime supervisors, service launchers, and operational scripts.
- `tests/` — automated tests.
- `scripts/` — maintained engineering, audit, migration, and verification utilities.
- `skills/` — NeginAI agent/skill definitions.
- `knowledge/` — curated knowledge/semantic assets.
- `migrations/` — durable migrations.
- `docs/` — current documentation, architecture notes, reports, handoffs, and design documentation.

## Local/runtime data — not canonical source

These directories may exist locally but must remain ignored by Git:

- `.runtime/` — disposable benchmarks, one-shot repair scripts, build logs, diagnostics.
- `.tmp/` — disposable scratch only.
- `logs/` — runtime logs.
- `artifacts/` — generated screenshots/exports/reference artifacts.
- `checkpoints/` — local rollback material.
- `visualizations/` — generated visual outputs.
- `data/` — runtime/local state except explicitly allow-listed canonical JSON files.
- `.venv/`, `node_modules/` — generated dependencies.
- `.tmp.driveupload/`, `.tmp.drivedownload/` — connector transfer scratch.

## Root policy

The repository root is reserved for project-wide configuration and entry documentation only. Do not place:

- one-off SQL/Python probes,
- generated CSV reports,
- build executables,
- temporary archives,
- inventory dumps,
- patch/base64 scratch,
- ad-hoc logs.

Use `.runtime/` for disposable engineering work and `docs/reports/` for reports that are intentionally part of the project.

## Safety rules

1. Never delete unknown project material directly; quarantine it outside the repository first.
2. Keep Varanegar/NGT/GRS data access read-only unless explicitly authorized otherwise.
3. Before cleanup commits, verify backend health, frontend typecheck/build, and the public vNext domain.
4. Use a Git checkpoint before structural cleanup or large moves.
5. Do not commit generated/runtime state merely to make the repository look complete.
