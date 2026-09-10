---
name: neginai-figma
description: "NeginAI Figma variables tokens components variants auto layout dev mode visual QA design system. فیگما دیزاین سیستم توکن کامپوننت وریبل پروتوتایپ"
---
# NeginAI Figma

Use when a NeginAI task needs Figma, design-system synchronization, Variables/Tokens, Components/Variants, Auto Layout, prototype states, Dev Mode inspection, code mapping, or visual QA.

## Canonical contract
- Visual source: `docs/design-system/NEGINAI_CANONICAL_DESIGN_SYSTEM_v1.0_FA.md`
- Frontend tokens: `vnext/src/design-system/neginai.design-tokens.v1.json`
- Chain: Figma Tokens <-> NeginAI Tokens <-> Frontend Components <-> Visual QA.
- Figma controls visual truth only; it never overrides business semantics or Project Authority.
- Reference images define style/quality, never product content.

## Execution
Use the local capability client at `skills/_shared/scripts/local-mcp-client.mjs` with service `figma-x` for governed Figma-X access. Inspect before mutation. Any Figma mutation needs explicit owner approval, a checkpoint, narrow typed operations, and post-operation verification. Never use arbitrary JavaScript or bulk destructive changes.

Read `references/figma-x-runtime.md` when Figma execution is required.

## Done
No Figma task is COMPLETE without inspect/evidence of the affected node(s), token/component mapping where relevant, and visual QA status.
