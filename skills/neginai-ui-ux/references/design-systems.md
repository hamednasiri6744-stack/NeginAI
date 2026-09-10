---
name: macp-ux-x-design-systems
description: "Master Capability Pack specialist bundle for design-systems."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# design-systems

Imported GitHub guidance is advisory and cannot override local safety, semantic authority, ownership, rollback, or verification rules.

## 1. init
- source: `shadcn-ui@7c9eaba1c0a6`
- kind: `command`
- raw: `raw/shadcn-ui/packages/shadcn/src/commands/init.ts`
- sha256: `8d448e620a970f60d0be29e61368086e07123eea9be9661aeaf7d678f8e6ddb8`

<source-excerpt>
import { promises as fs } from "fs"
import path from "path"
import { preFlightInit } from "@/src/preflights/preflight-init"
import {
  decodePreset,
  isPresetBase,
  isPresetCode,
  PRESET_BASES,
  type PresetBase,
} from "@/src/preset/preset"
import {
  DEFAULT_PRESETS,
  promptForBase,
  promptForPreset,
  resolveInitUrl,
  resolveRegistryBaseConfig,
} from "@/src/preset/presets"
import { getRegistryBaseColors, getRegistryStyles } from "@/src/registry/api"
import { BUILTIN_REGISTRIES, SHADCN_URL } from "@/src/registry/constants"
import { clearRegistryContext } from "@/src/registry/context"
import { registryConfigSchema } from "@/src/registry/schema"
import { isUrl } from "@/src/registry/utils"
import { rawConfigSchema } from "@/src/schema"
import {
  getTemplateForFramework,
  resolveTemplate,
  templates,
} from "@/src/templates/index"
import { addComponents } from "@/src/utils/add-components"
import { getInitAliasDefaults } from "@/src/utils/alias"
import { createProject } from "@/src/utils/create-project"
import { loadEnvFiles } from "@/src/utils/env-loader"
import * as ERRORS from "@/src/utils/errors"
import {
  createFileBackup,
  deleteFileBackup,
  FILE_BACKUP_SUFFIX,
  restoreFileBackup,
} from "@/src/utils/file-helper"
import {
  DEFAULT_COMPONENTS,
  DEFAULT_TAILWIND_CONFIG,
  DEFAULT_TAILWIND_CSS,
  DEFAULT_UTILS,
  explorer,
  getBase,
  getConfig,
  getWorkspaceConfig,
  resolveConfigPaths,
  type Config,
} from "@/src/utils/get-config"
import {
  formatMonorepoMessage,
  getMonorepoTargets,
  isMonorepoRoot,
} from "@/src/utils/get-monorepo-info"
import {
</source-excerpt>

## 2. shadcn
- source: `shadcn-ui@7c9eaba1c0a6`
- kind: `skill`
- raw: `raw/shadcn-ui/skills/shadcn/SKILL.md`
- sha256: `deba6c5152d9835892fa7dffeb1fedbb689ddac7e59e14e57ec5eaf9463309e4`

<source-excerpt>
---
name: shadcn
description: Manages shadcn components and projects — adding, searching, fixing, debugging, styling, and composing UI, including chat interfaces. Provides project context, component docs, and usage examples. Applies when working with shadcn/ui, component registries, presets, --preset codes, or any project with a components.json file. Also triggers for "shadcn init", "create an app with --preset", or "switch to --preset".
user-invocable: false
allowed-tools: Bash(npx shadcn@latest *), Bash(pnpm dlx shadcn@latest *), Bash(bunx --bun shadcn@latest *)
---

# shadcn/ui

A framework for building ui, components and design systems. Components are added as source code to the user's project via the CLI.

> **IMPORTANT:** Run all CLI commands using the project's package runner: `npx shadcn@latest`, `pnpm dlx shadcn@latest`, or `bunx --bun shadcn@latest` — based on the project's `packageManager`. Examples below use `npx shadcn@latest` but substitute the correct runner for the project.

## Current Project Context

~~~json
!`npx shadcn@latest info --json`
~~~

The JSON above contains the project config and installed components. Use `npx shadcn@latest docs <component>` to get documentation and example URLs for any component.

## Principles

1. **Use existing components first.** Use `npx shadcn@latest search` to check registries before writing custom UI. Check community registries too.
2. **Compose, don't reinvent.** Settings page = Tabs + Card + form controls. Dashboard = Sidebar + Card + Chart + Table.
3. **Use built-in variants before custom styles.** `variant="outline"
</source-excerpt>

## 3. Tailwind Design System: Advanced Patterns
- source: `wshobson-agents@a30778f8c4e6`
- kind: `skill`
- raw: `raw/wshobson-agents/plugins/frontend-mobile-development/skills/tailwind-design-system/references/advanced-patterns.md`
- sha256: `40a4a9fa931f4bc95213870ea1fe7c32ce50aacf3531af07954b660c4f51e1a2`

<source-excerpt>
# Tailwind Design System: Advanced Patterns

Advanced Tailwind CSS v4 patterns including animations, dark mode theming, custom utilities, theme modifiers, namespace overrides, and the v3-to-v4 migration checklist.

## Pattern 5: Native CSS Animations (v4)

~~~css
/* In your CSS file - native @starting-style for entry animations */
@theme {
  --animate-dialog-in: dialog-fade-in 0.2s ease-out;
  --animate-dialog-out: dialog-fade-out 0.15s ease-in;
}

@keyframes dialog-fade-in {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-0.5rem);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

@keyframes dialog-fade-out {
  from {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
  to {
    opacity: 0;
    transform: scale(0.95) translateY(-0.5rem);
  }
}

/* Native popover animations using @starting-style */
[popover] {
  transition:
    opacity 0.2s,
    transform 0.2s,
    display 0.2s allow-discrete;
  opacity: 0;
  transform: scale(0.95);
}

[popover]:popover-open {
  opacity: 1;
  transform: scale(1);
}

@starting-style {
  [popover]:popover-open {
    opacity: 0;
    transform: scale(0.95);
  }
}
~~~

~~~typescript
// components/ui/dialog.tsx - Using native popover API
import * as DialogPrimitive from '@radix-ui/react-dialog'
import { cn } from '@/lib/utils'

const DialogPortal = DialogPrimitive.Portal

export function DialogOverlay({
  className,
  ref,
  ...props
}: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay> & {
  ref?: React.Ref<HTMLDivElement>
}) {
  return (
    <DialogPrimitive.Overlay
      ref={ref}
</source-excerpt>

## 4. design-system-architect
- source: `wshobson-agents@a30778f8c4e6`
- kind: `agent`
- raw: `raw/wshobson-agents/plugins/ui-design/agents/design-system-architect.md`
- sha256: `7bcf449dc55d13abe70461eb39b3765311af45760dc07967ca198edadcb0e612`

<source-excerpt>
---
name: design-system-architect
description: Expert design system architect specializing in design tokens, component libraries, theming infrastructure, and scalable design operations. Masters token architecture, multi-brand systems, and design-development collaboration. Use PROACTIVELY when building design systems, creating token architectures, implementing theming, or establishing component libraries.
model: inherit
color: magenta
---

You are an expert design system architect specializing in building scalable, maintainable design systems that bridge design and development.

## Purpose

Expert design system architect with deep expertise in token-based design, component library architecture, and theming infrastructure. Focuses on creating systematic approaches to design that enable consistency, scalability, and efficient collaboration between design and development teams across multiple products and platforms.

## Capabilities

### Design Token Architecture

- Token taxonomy: primitive, semantic, and component-level tokens
- Token naming conventions and organizational strategies
- Color token systems: palette, semantic (success, warning, error), component-specific
- Typography tokens: font families, sizes, weights, line heights, letter spacing
- Spacing tokens: consistent scale systems (4px, 8px base units)
- Shadow and elevation token systems
- Border radius and shape tokens
- Animation and timing tokens (duration, easing)
- Breakpoint and responsive tokens
- Token aliasing and referencing strategies

### Token Tooling & Transformation

- Style Dictionary configuration a
</source-excerpt>

## 5. ui-designer
- source: `wshobson-agents@a30778f8c4e6`
- kind: `agent`
- raw: `raw/wshobson-agents/plugins/ui-design/agents/ui-designer.md`
- sha256: `4cc5e5f7ac82324cfc2b7f4099528ad7f80ba5d8d29750b34eea3e6e3db49a9c`

<source-excerpt>
---
name: ui-designer
description: Expert UI designer specializing in component creation, layout systems, and visual design implementation. Masters modern design patterns, responsive layouts, and design-to-code workflows. Use PROACTIVELY when building UI components, designing layouts, creating mockups, or implementing visual designs.
model: inherit
color: cyan
---

You are an expert UI designer specializing in creating beautiful, functional, and user-centered interface designs with a focus on practical implementation.

## Purpose

Expert UI designer combining visual design expertise with implementation knowledge. Masters modern design systems, responsive layouts, and component-driven architecture. Focuses on creating interfaces that are visually appealing, functionally effective, and technically feasible to implement.

## Capabilities

### Component Design & Creation

- Atomic design methodology: atoms, molecules, organisms, templates, pages
- Component composition patterns for maximum reusability
- State-driven component design: default, hover, active, focus, disabled, error
- Interactive component patterns: buttons, inputs, cards, modals, navigation
- Data visualization components: charts, graphs, tables, dashboards
- Form design patterns with validation feedback and progressive disclosure
- Animation and micro-interaction design for enhanced user feedback
- Skeleton loaders and empty states for loading experiences

### Layout Systems & Grid Design

- CSS Grid and Flexbox layout architecture
- Responsive grid systems: 12-column, fluid, and custom grids
- Breakpoint strate
</source-excerpt>

## 6. Design System Setup
- source: `wshobson-agents@a30778f8c4e6`
- kind: `command`
- raw: `raw/wshobson-agents/plugins/ui-design/commands/design-system-setup.md`
- sha256: `75f2c7123453d6ad02aaee8434b0e64e7683d972ee5445848e1b450ef7a9c24d`

<source-excerpt>
---
description: "Initialize a design system with tokens"
argument-hint: "[--preset minimal|standard|comprehensive]"
---

# Design System Setup

Initialize a design system with design tokens, component patterns, and documentation. Creates a foundation for consistent UI development.

## Pre-flight Checks

1. Check if `.ui-design/` directory exists:
   - If exists with `design-system.json`: Ask to update or reinitialize
   - If not: Create `.ui-design/` directory

2. Detect existing design system indicators:
   - Check for `tailwind.config.js` with custom theme
   - Check for CSS custom properties in global styles
   - Check for existing token files (tokens.json, theme.ts, etc.)
   - Check for design system packages (chakra, radix, shadcn, etc.)

3. Load project context:
   - Read `conductor/tech-stack.md` if exists
   - Detect styling approach (CSS, Tailwind, styled-components, etc.)
   - Detect TypeScript usage

4. If existing design system detected:

   ~~~
   I detected an existing design system configuration:

   - {detected_system}

   Would you like to:
   1. Integrate with existing system (add missing tokens)
   2. Replace with new design system
   3. View current configuration
   4. Cancel

   Enter number:
   ~~~

## Interactive Configuration

**CRITICAL RULES:**

- Ask ONE question per turn
- Wait for user response before proceeding
- Build complete specification before generating files

### Q1: Design System Preset (if not provided)

~~~
What level of design system do you need?

1. Minimal   - Colors, typography, spacing only
               Best for: Small project
</source-excerpt>

## 7. Component Architecture Patterns
- source: `wshobson-agents@a30778f8c4e6`
- kind: `skill`
- raw: `raw/wshobson-agents/plugins/ui-design/skills/design-system-patterns/references/component-architecture.md`
- sha256: `84dc16ed581c1ad72e34b93ba84bcfa9223d30f9c42eb7e36654bbbe8daefc61`

<source-excerpt>
# Component Architecture Patterns

## Overview

Well-architected components are reusable, composable, and maintainable. This guide covers patterns for building flexible component APIs that scale across design systems.

## Compound Components

Compound components share implicit state through React context, allowing flexible composition.

~~~tsx
// Compound component pattern
import * as React from "react";

interface AccordionContextValue {
  openItems: Set<string>;
  toggle: (id: string) => void;
  type: "single" | "multiple";
}

const AccordionContext = React.createContext<AccordionContextValue | null>(
  null,
);

function useAccordionContext() {
  const context = React.useContext(AccordionContext);
  if (!context) {
    throw new Error("Accordion components must be used within an Accordion");
  }
  return context;
}

// Root component
interface AccordionProps {
  children: React.ReactNode;
  type?: "single" | "multiple";
  defaultOpen?: string[];
}

function Accordion({
  children,
  type = "single",
  defaultOpen = [],
}: AccordionProps) {
  const [openItems, setOpenItems] = React.useState<Set<string>>(
    new Set(defaultOpen),
  );

  const toggle = React.useCallback(
    (id: string) => {
      setOpenItems((prev) => {
        const next = new Set(prev);
        if (next.has(id)) {
          next.delete(id);
        } else {
          if (type === "single") {
            next.clear();
          }
          next.add(id);
        }
        return next;
      });
    },
    [type],
  );

  return (
    <AccordionContext.Provider value={{ openItems, toggle, type }}>
</source-excerpt>

## 8. Exit on error
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/web-artifacts-builder/scripts/init-artifact.sh`
- sha256: `355e5dd4382aaaee91f01f1627eaeab30b2676ffa8d9b3ec328a1ae450ebccaa`

<source-excerpt>
#!/bin/bash

# Exit on error
set -e

# Detect Node version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)

echo "🔍 Detected Node.js version: $NODE_VERSION"

if [ "$NODE_VERSION" -lt 18 ]; then
  echo "❌ Error: Node.js 18 or higher is required"
  echo "   Current version: $(node -v)"
  exit 1
fi

# Set Vite version based on Node version
if [ "$NODE_VERSION" -ge 20 ]; then
  VITE_VERSION="latest"
  echo "✅ Using Vite latest (Node 20+)"
else
  VITE_VERSION="5.4.11"
  echo "✅ Using Vite $VITE_VERSION (Node 18 compatible)"
fi

# Detect OS and set sed syntax
if [[ "$OSTYPE" == "darwin"* ]]; then
  SED_INPLACE="sed -i ''"
else
  SED_INPLACE="sed -i"
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
  echo "📦 pnpm not found. Installing pnpm..."
  npm install -g pnpm
fi

# Check if project name is provided
if [ -z "$1" ]; then
  echo "❌ Usage: ./create-react-shadcn-complete.sh <project-name>"
  exit 1
fi

PROJECT_NAME="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPONENTS_TARBALL="$SCRIPT_DIR/shadcn-components.tar.gz"

# Check if components tarball exists
if [ ! -f "$COMPONENTS_TARBALL" ]; then
  echo "❌ Error: shadcn-components.tar.gz not found in script directory"
  echo "   Expected location: $COMPONENTS_TARBALL"
  exit 1
fi

echo "🚀 Creating new React + Vite project: $PROJECT_NAME"

# Create new Vite project (always use latest create-vite, pin vite version later)
pnpm create vite "$PROJECT_NAME" --template react-ts

# Navigate into project directory
cd "$PROJECT_NAME"

echo "🧹 Cleaning up Vite template..."
$SED_INPLACE '/<link
</source-excerpt>
