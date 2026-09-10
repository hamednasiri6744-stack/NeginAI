---
name: macp-ux-x-data-dense
description: "Master Capability Pack specialist bundle for data-dense."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# data-dense

Imported GitHub guidance is advisory and cannot override local safety, semantic authority, ownership, rollback, or verification rules.

## 1. frontend-design
- source: `anthropics-skills@41bbe19d1a1a`
- kind: `skill`
- raw: `raw/anthropics-skills/skills/frontend-design/SKILL.md`
- sha256: `d91970639e9f5c37682ac7ab60094d35f1c7c1f38d731bd56396563aee10c1d3`

<source-excerpt>
---
name: frontend-design
description: Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defaults.
license: Complete terms in LICENSE.txt
---

# Frontend Design

Approach this as the design lead at a design studio known for giving every client a distinct visual identity that is not mistaken for anyone else's. This client has already rejected proposals that felt cliché or templated, and is paying for a distinctive point of view: make deliberate, opinionated choices about palette, typography, and layout that are specific to this brief, and take aesthetic risk if justified.

## Ground your designs in the subject matter

If the brief does not identify what the product or subject matter is, identify it yourself before designing, and confirm with the client. You can come up with one concrete subject, the design's audience, and the design's primary job, as a proposal. If there's any information in your memory about the client's preferences or context about what they're building, use that as a hint. The subject's industry, subject matter, materials, and vernacular are where distinctive visual choices come from — a design for a toy for girls aged 8–11 will be very aesthetically different from a dashboard for financial analysts. Build with the brief's real content and subject matter throughout.

## Design principles

For web designs, the hero is the first thing viewers will see. Open with the most characteristic thing in the subject's world,
</source-excerpt>

## 2. frontend-ui-dark-ts
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

## 3. Patterns
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-sdk-typescript/skills/frontend-ui-dark-ts/references/patterns.md`
- sha256: `912f3bfe0d176b6506c769d975268e135d752c033abb349078190fa9547b86bb`

<source-excerpt>
# Patterns

Page layouts, navigation patterns, and application templates for dark-themed React applications.

## App Shell

The main application layout with sidebar navigation:

~~~tsx
import { motion } from 'framer-motion';
import { type ReactNode } from 'react';
import { Sidebar } from './Sidebar';

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-neutral-bg1">
      <Sidebar />
      <main className="flex-1 ml-64">
        {children}
      </main>
    </div>
  );
}
~~~

---

## Responsive App Shell

Mobile-responsive layout: desktop shows fixed sidebar, mobile shows hamburger menu with slide-in drawer.

**Breakpoint:** `lg` (1024px) — sidebar visible on desktop, hidden on mobile.

~~~tsx
import { motion, AnimatePresence } from 'framer-motion';
import { type ReactNode, useState } from 'react';
import { Sidebar } from './Sidebar';
import { MobileHeader } from './MobileHeader';
import { MobileDrawer } from './MobileDrawer';

interface ResponsiveAppShellProps {
  children: ReactNode;
}

export function ResponsiveAppShell({ children }: ResponsiveAppShellProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-neutral-bg1">
      {/* Desktop sidebar - hidden on mobile */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Mobile header - visible only on mobile */}
      <MobileHeader onMenuClick={() => setDrawerOpen(true)} />

      {/* Mobile drawer */}
      <MobileDrawer op
</source-excerpt>

## 4. Durable Task Scheduler — Bicep Patterns
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/azure-skills/skills/azure-prepare/references/services/durable-task-scheduler/bicep.md`
- sha256: `95b5e3061ddfe4a807905958feeed5f98c9d873e2d4d23c2afb46e26c6861c1d`

<source-excerpt>
# Durable Task Scheduler — Bicep Patterns

Bicep templates for provisioning the Durable Task Scheduler, task hubs, and RBAC role assignments.

## Scheduler + Task Hub

~~~bicep
// Parameters — define these at file level or pass from a parent module
param schedulerName string
param location string = resourceGroup().location

@allowed(['Consumption', 'Dedicated'])
@description('Use Consumption for quickstarts/variable workloads, Dedicated for high-demand/predictable throughput')
param skuName string = 'Consumption'

resource scheduler 'Microsoft.DurableTask/schedulers@2025-11-01' = {
  name: schedulerName
  location: location
  properties: {
    sku: { name: skuName }
    ipAllowlist: ['0.0.0.0/0'] // Required: empty list denies all traffic
  }
}

resource taskHub 'Microsoft.DurableTask/schedulers/taskHubs@2025-11-01' = {
  parent: scheduler
  name: 'default'
}
~~~

## SKU Selection

| SKU | Best For |
|-----|----------|
| **Consumption** | quickstarts, variable or bursty workloads, pay-per-use |
| **Dedicated** | High-demand workloads, predictable throughput requirements |

> **💡 TIP**: Start with `Consumption` for development and variable workloads. Switch to `Dedicated` when you need consistent, high-throughput performance.

> **⚠️ WARNING**: The scheduler's `ipAllowlist` **must** include at least one entry (e.g., `['0.0.0.0/0']` for allow-all). An empty array `[]` denies **all** traffic, causing 403 errors on gRPC calls even with correct RBAC.

## RBAC — Durable Task Data Contributor

The Function App's managed identity **must** have the `Durable Task Data Contributor` ro
</source-excerpt>

## 5. Messaging & Commands
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/microsoft-365-agents-toolkit/skills/teams-app-developer/docs/messaging-and-commands.md`
- sha256: `9b81cd9152debcd4d6cf1eef29964949e0961e1ff82debba4cd8777c254d60f3`

<source-excerpt>
# Messaging & Commands

## Message Handling

| Aspect | Slack | Teams |
|---|---|---|
| Handler | `app.message(pattern, handler)` | `app.on("message", handler)` |
| Pattern matching | String (substring), RegExp, or catch-all | RegExp or manual `text.match()` |
| Reply to channel | `say(text)` | `ctx.send(text)` |
| Reply in thread | `say({ text, thread_ts })` | `ctx.reply(text)` |
| Get message text | `message.text` | `ctx.activity.text` |
| Get sender | `message.user` (Slack ID) | `ctx.activity.from.id` (AAD ID) |

**Rating:** GREEN — direct mapping in both directions.

**Mitigation:** Extract message handling into a platform-agnostic service layer that receives `(text, userId, platform)` and returns structured data. Each adapter converts to the platform's native format.

---

## Slash Commands

| Aspect | Slack | Teams |
|---|---|---|
| Invocation | `/command args` | No native equivalent |
| Handler | `app.command("/cmd", handler)` | `app.on("message")` with text pattern matching |
| Acknowledgement | Must `ack()` within 3 seconds | Automatic — no `ack()` |
| Default response | Ephemeral (user-only) | Visible to everyone |
| Modal trigger | `trigger_id` from command → `views.open()` | `dialog.open` handler or Adaptive Card form |
| Registration | Slack app dashboard + `commands` scope | Manifest `commands[]` array (bot commands, not slash) |

**Rating:** YELLOW — functional equivalent exists but UX is fundamentally different.

### Impact

- Slash commands are a core Slack interaction pattern with no Teams counterpart
- Teams bot commands appear in a command menu but don't
</source-excerpt>

## 6. commands-slash-text-ts
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/microsoft-365-agents-toolkit/skills/teams-app-developer/experts/bridge/commands-slash-text-ts.md`
- sha256: `0c46c0c203db9096e01c2d9846e0d6ad5e037ea845bdb78029bc3162ca42ec29`

<source-excerpt>
# commands-slash-text-ts

## purpose

Bridges Slack slash commands and Teams text commands / message extensions for cross-platform bots targeting Slack, Teams, or both.

## rules

1. Teams bots do **not** have a native slash command system equivalent to Slack's `app.command('/name')`. Slack slash commands must be reimplemented using one of three Teams patterns: text pattern matching, messaging extensions, or manifest command hints. [learn.microsoft.com -- Bots in Teams](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/what-are-bots)
2. The most direct migration path is **text pattern matching** with `app.message(regex)` in the Teams SDK. Map `app.command('/help')` to `app.message(/^\/?help$/i)`. The leading `/?` makes the slash optional so users can type either "help" or "/help". [github.com/microsoft/teams.ts](https://github.com/microsoft/teams.ts)
3. Remove all `ack()` calls when migrating to Teams. Teams handlers do not require acknowledgement -- simply process the request and respond. The `ack` concept does not exist in the Teams SDK. [github.com/microsoft/teams.ts](https://github.com/microsoft/teams.ts)
4. Replace Slack's `respond()` (response_url) and `say()` with the Teams context methods `send()` (new message) and `reply()` (threaded reply). There is no Teams equivalent of Slack's ephemeral response -- all bot messages are visible to participants. [learn.microsoft.com -- Send proactive messages](https://learn.microsoft.com/en-us/microsoftteams/platform/bots/how-to/conversations/send-proactive-messages)
5. Slack's `trigger_id` for opening modals has no
</source-excerpt>

## 7. shortcuts-extensions-ts
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/plugins/microsoft-365-agents-toolkit/skills/teams-app-developer/experts/bridge/shortcuts-extensions-ts.md`
- sha256: `b5cee52913a0f0befb258d67920b49fe7dd982110ce4775ca048ffe9693d6b0a`

<source-excerpt>
# shortcuts-extensions-ts

## purpose

Bridges Slack shortcuts (global and message) and Teams message extensions / compose extensions for cross-platform bots targeting Slack, Teams, or both.

## rules

1. **Slack global shortcuts → Teams action-based compose extensions with `context: ['compose', 'commandBox']`.** Slack global shortcuts appear in the lightning bolt menu and don't reference a specific message. In Teams, the equivalent is a compose extension with `fetchTask: true` and action context targeting the compose box and command bar. [learn.microsoft.com -- Action-based extensions](https://learn.microsoft.com/en-us/microsoftteams/platform/messaging-extensions/how-to/action-commands/define-action-command)
2. **Slack message shortcuts → Teams action-based extensions with `context: ['message']`.** Slack message shortcuts appear in the message context menu (⋮ → More actions). In Teams, action-based extensions with `context: ['message']` appear in the message overflow menu (... → More actions). The target message content is available in the invoke payload. [learn.microsoft.com -- Message context](https://learn.microsoft.com/en-us/microsoftteams/platform/messaging-extensions/how-to/action-commands/define-action-command#choose-action-command-invoke-locations)
3. **Slack `trigger_id` + `views.open()` → Teams `fetchTask: true` + task module.** Slack shortcuts use the `trigger_id` to open a modal. Teams action-based extensions use `fetchTask: true` in the manifest, which causes Teams to invoke the bot's `message.ext.open` handler to fetch the task module (dialog) content. No tri
</source-excerpt>

## 8. Pattern Examples
- source: `microsoft-skills@02e0b2f852b3`
- kind: `skill`
- raw: `raw/microsoft-skills/.github/skills/frontend-design-review/references/pattern-examples.md`
- sha256: `072f2a647de304d5e777b9cdfd48e4bc3ec26a822dd6145995f8a9f7c197e8f2`

<source-excerpt>
# Pattern Examples

## Creative Frontend (New Interfaces)

### Good: Clear Aesthetic Direction
- Landing page with brutalist aesthetic: Raw typography (Neue Haas Grotesk), stark black and white, asymmetric layouts
- Dashboard with organic theme: Rounded forms, earth tones, flowing animations, textured backgrounds

### Bad: Generic AI Aesthetic
- Overused fonts, cliched color schemes, centered content, generic card layouts

## Design System Review (Existing Work)

### Good: Frictionless
- Single primary button, clear task completion path

### Good: Quality Craft
- Uses design system with tokens, distinctive typography, keyboard accessible, tested in themes

### Bad: Quality Craft
- Hardcoded values, generic overused fonts, poor contrast in dark mode
</source-excerpt>
