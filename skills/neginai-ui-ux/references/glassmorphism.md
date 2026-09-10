---
name: macp-ux-x-glassmorphism
description: "Master Capability Pack specialist bundle for glassmorphism."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# glassmorphism

Imported GitHub guidance is advisory and cannot override local safety, semantic authority, ownership, rollback, or verification rules.

## 1. frontend-ui-dark-ts
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-sdk-typescript/skills/frontend-ui-dark-ts/SKILL.md`
- sha256: `01b637359bcd70182a451b77d20d965cbd2476a4a994ae1ad0688eed640860f2`

<source-excerpt>
---
name: frontend-ui-dark-ts
description: Build dark-themed React applications using Tailwind CSS with custom theming, glassmorphism effects, and Framer Motion animations. Use when creating dashboards, admin panels, or data-rich interfaces with a refined dark aesthetic.
license: MIT
metadata:
  author: Microsoft
  version: "1.0.0"
---

# Frontend UI Dark Theme (TypeScript)

A modern dark-themed React UI system using **Tailwind CSS** and **Framer Motion**. Designed for dashboards, admin panels, and data-rich applications with glassmorphism effects and tasteful animations.

## Stack

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^18.x | UI framework |
| `react-dom` | ^18.x | DOM rendering |
| `react-router-dom` | ^6.x | Routing |
| `framer-motion` | ^11.x | Animations |
| `clsx` | ^2.x | Class merging |
| `tailwindcss` | ^3.x | Styling |
| `vite` | ^5.x | Build tool |
| `typescript` | ^5.x | Type safety |

## Quick Start

~~~bash
npm create vite@latest my-app -- --template react-ts
cd my-app
npm install framer-motion clsx react-router-dom
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
~~~

## Project Structure

~~~
public/
├── favicon.ico                    # Classic favicon (32x32)
├── favicon.svg                    # Modern SVG favicon
├── apple-touch-icon.png           # iOS home screen (180x180)
├── og-image.png                   # Social sharing image (1200x630)
└── site.webmanifest               # PWA manifest
src/
├── assets/
│   └── fonts/
│       ├── Segoe UI.ttf
│       ├── Segoe UI Bold.ttf
│       ├── Segoe U
</source-excerpt>

## 2. gem-designer
- source: `awesome-copilot@7b1ebe633339`
- kind: `agent`
- raw: `raw/awesome-copilot/agents/gem-designer.agent.md`
- sha256: `f132d91a18d16274ff44b2c1332efb9450fca1e6ec43dc7a32abfea24701706d`

<source-excerpt>
---
description: "UI/UX design specialist: layouts, themes, color schemes, design systems, accessibility."
name: gem-designer
argument-hint: "Enter execution_id, task_id, optional plan_id, task_definition, and role-scoped config_snapshot."
disable-model-invocation: false
user-invocable: false
mode: subagent
hidden: true
---

# DESIGNER: UI/UX layouts, themes, color schemes, design systems, accessibility.

<role>

## Role

Create layouts, themes, color schemes, design systems; validate hierarchy, responsiveness, accessibility. Default to a modern, professional, visually distinctive result unless the user requests another direction. Never implement code.

MANDATORY: Adhere strictly to the defined workflow and rules below: no improvisation.

</role>

<workflow>

## Workflow

- Load `gem-design-md-guidelines` skill.
- Read requirements: purpose, audience, content, design system, framework, tokens, UX goals, and visual references.
- Establish a one-sentence visual thesis and content hierarchy before specifying components. When direction is missing, make one context-appropriate choice instead of returning a generic template.
- Execute per skill: component specs, layout, theme, motion.
- Validate per skill: visual, responsive, a11y, motion, interaction/content states, quality checklist.
- Output: minimal JSON per `output_format`.

</workflow>

<output_format>

## Output Format

~~~json
{
  "status": "completed | failed | needs_revision",
  "task_id": "string",
  "fail": "transient | fixable | needs_replan | escalate | flaky | regression | new_failure | platform_specific",
  "mode"
</source-excerpt>

## 3. premium-frontend-ui
- source: `awesome-copilot@7b1ebe633339`
- kind: `skill`
- raw: `raw/awesome-copilot/skills/premium-frontend-ui/SKILL.md`
- sha256: `7c256bc86b193d75e4c7e97ba35b66acbbeaa547acef2cfca2844bf9e73eaaff`

<source-excerpt>
---
name: premium-frontend-ui
description: 'A comprehensive guide for GitHub Copilot to craft immersive, high-performance web experiences with advanced motion, typography, and architectural craftsmanship.'
metadata:
  author: 'Utkarsh Patrikar'
  author_url: 'https://github.com/utkarsh232005'
---

# Immersive Frontend UI Craftsmanship

As an AI engineering assistant, your role when building premium frontend experiences goes beyond outputting functional HTML and CSS. You must architect **immersive digital environments**. This skill provides the blueprint for generating highly intentional, award-level web applications that prioritize aesthetic quality, deep interactivity, and flawless performance.

When a user requests a high-end landing page, an interactive portfolio, or a specialized component that requires top-tier visual polish, apply the following rigorous standards to every line of code you generate.

---

## 1. Establishing the Creative Foundation

Before generating layout code, ensure you understand the core emotional resonance the UI should deliver. Do not default to generic, unopinionated code.

Commit to a strong visual identity in your CSS and component structure:
- **Editorial Brutalism**: High-contrast monochromatic palettes, oversized typography, sharp rectangular edges, and raw grid structures.
- **Organic Fluidity**: Soft gradients, deeply rounded corners, glassmorphism overlays, and bouncy spring-based physics.
- **Cyber / Technical**: Dark mode dominance, glowing neon accents, monospaced typography, and rapid, staggered reveal animations.
- **Cinematic Paci
</source-excerpt>
