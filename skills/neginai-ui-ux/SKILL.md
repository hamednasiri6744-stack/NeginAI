---
name: neginai-ui-ux
description: "NeginAI UI UX design system RTL responsive accessibility visual QA mobile enterprise glass neumorphism. رابط کاربری تجربه کاربری طراحی سیستم فارسی راست به چپ موبایل"
license: MIT
---
# NeginAI UI UX
Images define how NeginAI should look; Project Map defines what it contains and how it works. Never copy reference-image business content. Direction: 70% clean enterprise, 20% mild glass, 10% soft neumorphism; deep navy + restrained gold; avoid gaming/cyberpunk/generic admin. Mobile-first, RTL-first, accessible. Foundations -> Tokens -> Components -> Patterns -> Screens. Canonical: docs/design-system/NEGINAI_CANONICAL_DESIGN_SYSTEM_v1.0_FA.md and vnext/src/design-system/neginai.design-tokens.v1.json. Figma is supportive/control-plane when available, not a blocker.


## Expert reference pack
Before substantial UI/UX work, read only the relevant files under `skills/neginai-ui-ux/references/`: `ux-x-core.md`, `design-systems.md`, `accessibility.md`, `responsive.md`, `glassmorphism.md`, `neumorphism.md`, `motion.md`, `react-ui.md`, `data-dense.md`, `luxury.md`. Apply them under the NeginAI canonical rules above; generic reference guidance never overrides project authority or the canonical design system.

## Fast Visual Execution Loop
For active UI iteration, use the direct Vite HMR preview first; do not run a full production build after every micro-change. Batch coherent visual changes, validate in the fast preview, then build/deploy only at a checkpoint.
For any screen with an owner-approved reference image, that approved image is the screen-level visual authority for composition, proportion, hierarchy, density, surface treatment, and polish. The Design System supplies shared tokens/components; it must not dilute or reinterpret the approved visual target. Runtime screenshot comparison is required before declaring visual parity.
Avoid append-only CSS micro-patches. Consolidate changes into the owning design-system component before checkpoint build.
