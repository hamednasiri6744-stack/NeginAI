---
name: macp-ux-x-responsive
description: "Master Capability Pack specialist bundle for responsive."
category: "master-capability-pack"
pack_version: "macp-20260905-040932"
---

# responsive

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

## 2. Presenter Mode Developer
- source: `microsoft-skills@02e0b2f852b3`
- kind: `agent`
- raw: `raw/microsoft-skills/.github/agents/presenter.agent.md`
- sha256: `7e4ce269fd2edadb5b73ab866b3dad57468951ed8f991311a5c192de3b4be4e7`

<source-excerpt>
---
name: Presenter Mode Developer
description: Specialist for CoreAI DIY presenter mode features, including presentation view, navigation, and teleprompter functionality
tools: ["read", "edit", "search", "execute"]
---

You are a **Presenter Mode Specialist** for the CoreAI DIY project. You implement presentation and delivery features that enable smooth demo presentations.

## Presenter Mode Features

### Core Components
- **PresenterView**: Full-screen presentation interface
- **PresenterSidebar**: Navigation panel with node overview
- **PresenterSlide**: Individual node presentation
- **Teleprompter**: Script display for presenter
- **Keyboard Navigation**: Arrow keys, space for next/prev

### Canvas Modes
~~~typescript
type CanvasMode = 'viewing' | 'editing';

// Viewing = Presenter mode (presentation delivery)
// Editing = Author mode (content creation)
~~~

## File Locations

| Purpose | Path |
|---------|------|
| Presenter Components | `src/frontend/src/components/presenter/` |
| Canvas Mode Toggle | `src/frontend/src/components/canvas/CanvasHeader.tsx` |
| App Store (mode) | `src/frontend/src/store/app-store.ts` |

## Key Patterns

### Mode-Aware Components
~~~typescript
export const VideoNode = memo(function VideoNode({ id, data, selected }: Props) {
  const canvasMode = useAppStore((state) => state.canvasMode);

  return (
    <>
      {/* Only show resizer in editing mode */}
      {canvasMode === 'editing' && (
        <NodeResizer isVisible={selected} />
      )}

      {/* Mode-specific UI */}
      <div className={cn(
        'node-container',
        canvas
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

## 4. SkillsSection
- source: `microsoft-skills@02e0b2f852b3`
- kind: `guide`
- raw: `raw/microsoft-skills/docs-site/src/components/SkillsSection.tsx`
- sha256: `659427e24ecd34e6c5f2bf83729e49ab01ac37f5ea30ca899c98427af740256a`

<source-excerpt>
import { useState, useMemo, useCallback, useEffect } from 'react';
import { LanguageTabs, type Language } from './LanguageTabs';
import { CategoryTabs, type Category } from './CategoryTabs';
import { SearchInput } from './SearchInput';
import { SkillCard, type Skill } from './SkillCard';
import { SkillDetailModal } from './SkillDetailModal';

interface SkillInput {
  name: string;
  description: string;
  lang: string;
  category: string;
  path?: string;
  package?: string;
}

interface SkillsSectionProps {
  skills: SkillInput[];
}

const LANG_DISPLAY: Record<string, string> = {
  py: 'Python',
  dotnet: '.NET',
  ts: 'TypeScript',
  java: 'Java',
  rust: 'Rust',
  core: 'Core',
};

function getSkillFromHash(): string | null {
  if (typeof window === 'undefined') return null;
  const hash = window.location.hash;
  if (hash.startsWith('#skill=')) {
    return decodeURIComponent(hash.slice('#skill='.length));
  }
  return null;
}

export function SkillsSection({ skills }: SkillsSectionProps) {
  const [selectedLang, setSelectedLang] = useState<Language>('all');
  const [selectedCategory, setSelectedCategory] = useState<Category>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  // On mount, check URL hash for a skill deep link
  useEffect(() => {
    const openSkillFromHash = () => {
      const skillName = getSkillFromHash();
      if (!skillName) return;
      const found = skills.find(s => s.name === skillName);
      if (found)
</source-excerpt>

## 5. rendering-usetransition-loading
- source: `vercel-agent-skills@063bee94c3f4`
- kind: `skill`
- raw: `raw/vercel-agent-skills/skills/react-best-practices/rules/rendering-usetransition-loading.md`
- sha256: `4fddb807812b133b478d42bdbfd34d4e0389ca73f18f544d5f1fd419cffc2aa2`

<source-excerpt>
---
title: Use useTransition Over Manual Loading States
impact: LOW
impactDescription: reduces re-renders and improves code clarity
tags: rendering, transitions, useTransition, loading, state
---

## Use useTransition Over Manual Loading States

Use `useTransition` instead of manual `useState` for loading states. This provides built-in `isPending` state and automatically manages transitions.

**Incorrect (manual loading state):**

~~~tsx
function SearchResults() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  const handleSearch = async (value: string) => {
    setIsLoading(true)
    setQuery(value)
    const data = await fetchResults(value)
    setResults(data)
    setIsLoading(false)
  }

  return (
    <>
      <input onChange={(e) => handleSearch(e.target.value)} />
      {isLoading && <Spinner />}
      <ResultsList results={results} />
    </>
  )
}
~~~

**Correct (useTransition with built-in pending state):**

~~~tsx
import { useTransition, useState } from 'react'

function SearchResults() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [isPending, startTransition] = useTransition()

  const handleSearch = (value: string) => {
    setQuery(value) // Update input immediately

    startTransition(async () => {
      // Fetch and update results
      const data = await fetchResults(value)
      setResults(data)
    })
  }

  return (
    <>
      <input onChange={(e) => handleSearch(e.target.value)} />
      {isPending && <Spinner
</source-excerpt>

## 6. rerender-transitions
- source: `vercel-agent-skills@063bee94c3f4`
- kind: `skill`
- raw: `raw/vercel-agent-skills/skills/react-best-practices/rules/rerender-transitions.md`
- sha256: `60f4033909a62df5e5b8c601494f9e50a562e2f8c1c2d81eac24f38142265f1c`

<source-excerpt>
---
title: Use Transitions for Non-Urgent Updates
impact: MEDIUM
impactDescription: maintains UI responsiveness
tags: rerender, transitions, startTransition, performance
---

## Use Transitions for Non-Urgent Updates

Mark frequent, non-urgent state updates as transitions to maintain UI responsiveness.

**Incorrect (blocks UI on every scroll):**

~~~tsx
function ScrollTracker() {
  const [scrollY, setScrollY] = useState(0)
  useEffect(() => {
    const handler = () => setScrollY(window.scrollY)
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])
}
~~~

**Correct (non-blocking updates):**

~~~tsx
import { startTransition } from 'react'

function ScrollTracker() {
  const [scrollY, setScrollY] = useState(0)
  useEffect(() => {
    const handler = () => {
      startTransition(() => setScrollY(window.scrollY))
    }
    window.addEventListener('scroll', handler, { passive: true })
    return () => window.removeEventListener('scroll', handler)
  }, [])
}
~~~
</source-excerpt>

## 7. use-mobile
- source: `shadcn-ui@7c9eaba1c0a6`
- kind: `hook`
- raw: `raw/shadcn-ui/apps/v4/hooks/use-mobile.ts`
- sha256: `ff44ea76ec603273e44dc66adfa816749812ca174414bce67aa7fbcf95336854`

<source-excerpt>
import * as React from "react"

export function useIsMobile(mobileBreakpoint = 768) {
  const [isMobile, setIsMobile] = React.useState<boolean | undefined>(undefined)

  React.useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${mobileBreakpoint - 1}px)`)
    const onChange = () => {
      setIsMobile(window.innerWidth < mobileBreakpoint)
    }
    mql.addEventListener("change", onChange)
    setIsMobile(window.innerWidth < mobileBreakpoint)
    return () => mql.removeEventListener("change", onChange)
  }, [mobileBreakpoint])

  return !!isMobile
}
</source-excerpt>

## 8. react-hook-form
- source: `shadcn-ui@7c9eaba1c0a6`
- kind: `hook`
- raw: `raw/shadcn-ui/apps/v4/content/docs/forms/react-hook-form.mdx`
- sha256: `23dc9a437a661f7475b0f2469738899c66487e5459a4c13594af0fba5aa06857`

<source-excerpt>
---
title: React Hook Form
description: Build forms in React using React Hook Form and Zod.
links:
  doc: https://react-hook-form.com
---

import { InfoIcon } from "lucide-react"

In this guide, we will take a look at building forms with React Hook Form. We'll cover building forms with the `<Field />` component, adding schema validation using Zod, error handling, accessibility, and more.

## Demo

We are going to build the following form. It has a simple text input and a textarea. On submit, we'll validate the form data and display any errors.

<Callout icon={<InfoIcon />}>
  **Note:** For the purpose of this demo, we have intentionally disabled browser
  validation to show how schema validation and form errors work in React Hook
  Form. It is recommended to add basic browser validation in your production
  code.
</Callout>

<ComponentPreview
  styleName="new-york-v4"
  name="form-rhf-demo"
  className="sm:[&_.preview]:h-[700px]"
  chromeLessOnMobile
/>

## Approach

This form leverages React Hook Form for performant, flexible form handling. We'll build our form using the `<Field />` component, which gives you **complete flexibility over the markup and styling**.

- Uses React Hook Form's `useForm` hook for form state management.
- `<Controller />` component for controlled inputs.
- `<Field />` components for building accessible forms.
- Client-side validation using Zod with `zodResolver`.

## Anatomy

Here's a basic example of a form using the `<Controller />` component from React Hook Form and the `<Field />` component.

~~~tsx showLineNumbers {5-18}
<Controller
  name="t
</source-excerpt>
