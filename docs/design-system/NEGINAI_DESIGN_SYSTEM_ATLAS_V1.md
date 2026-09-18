# NeginAI Design System Atlas v1

**Status:** Canonical UI/UX design language baseline  
**Date:** 2026-09-18  
**Direction:** Spatial Enterprise Neo + Living UI + Tactile Glass + Connected Surfaces  
**Scope:** Entire NeginAI product ecosystem

## Non-negotiable principles

- App-like, workflow-first, anti-dashboard.
- Depth replaces unnecessary mobile page length.
- Living UI communicates state; it is not decorative animation.
- Connected surfaces replace card-everywhere layouts.
- Premium Enterprise + Calm Futurism + Tech Minimal + Soft UI.
- Glass creates hierarchy/continuity; tactile treatment is reserved for interactive controls.
- Mobile-first, RTL-first, accessible, performant.
- No feature may be removed during visual migration.
- Product/business semantics remain owned by canonical backend/semantic contracts.

## 32 design pillars
1. Visual Style — Premium Enterprise · Calm Futurism · Tech Minimal · Soft UI
2. Material / Surface — Layered Glass · Frosted Glass · Acrylic · Matte
3. Physical / Tactile Feel — Tactile UI · Pressable · Raised · Inset
4. Screen / Product Architecture — App · Workspace · Command Center · Cockpit
5. Layout — Responsive Grid · Stack · Master Detail · Bento
6. Depth / Information Architecture — Surface → Stack → Sheet → Detail
7. Interaction — Tap · Swipe · Drag · Long Press · Inline Edit
8. Motion / Living UI — State-driven · Ambient · Event-driven · Microinteraction
9. Transitions — Continuity · Shared Element · Morph · Reveal
10. Dynamic Behavior — Adaptive · Contextual · Predictive · Reactive
11. Navigation — Bottom Nav · Context Bar · Drawer · Command Palette
12. Mobile App Structure — Safe Area · Bottom Dock · Sheets · Sticky CTA
13. Surface / Container Types — Stage · Panel · Sheet · Floating · Inset
14. Anti-Dashboard / App-Like Design — Workflow-first · Connected Surfaces · Progressive Disclosure
15. Density — Compact · Comfortable · Spacious · Adaptive
16. Spacing / Empty Space — 4/8 grid · Breathing Room · Rhythm
17. Visual Hierarchy — Focus · Contrast · Scale · Proximity
18. Typography — Vazirmatn · Inter · Type Scale · Numeric Emphasis
19. Color — Navy · Gold · Mint · Semantic Colors
20. UI States — Default · Hover · Focus · Pressed · Disabled · Loading · Updating
21. Business / Commercial States — Draft · Credit Risk · Opportunity · Visit Outcome
22. Feedback Components — Toast · Banner · Inline Alert · Skeleton · Empty
23. Form Controls — Input · Select · Stepper · Picker · Validation
24. Data Display — Metric · KPI · Progress · Trend · Table · Chart
25. Customer / Entity UI — Entity Header · Customer 360 · Context Strip · Timeline
26. AI UI — Copilot · AI Panel · Explain · Sources · Thinking
27. Intelligence / Recommendation — Next Best Action · Opportunity · Risk · Explanation
28. Responsive Design — Mobile-first · Fluid · Breakpoint-aware · Reflow
29. RTL / Bidirectional — RTL-first · Numeric LTR · Icon Mirroring · Mixed Content
30. Accessibility — Keyboard · Focus · Contrast · Labels · Reduced Motion
31. Performance UI — Skeleton · Lazy · Virtualized · Optimistic · Cached
32. Styles Especially Relevant to NeginAI — Spatial Enterprise Neo · Living UI · Tactile Glass · Connected Surfaces

## Canonical surface grammar
Use:
```
Stage
  → Surface / Connected Stack
    → Detail Layer
      → Floating Surface / Sheet / Focus Layer
```

Avoid:
- unrelated card grids,
- dead decorative KPI cards,
- long vertical pages when depth can preserve context,
- motion without semantic state,
- gold saturation across large surfaces,
- local per-screen token inventions.

## Component families

The design system recognizes 40 component families:
App Shell, Top Navigation, Bottom Navigation, Side Navigation, Tabs, Navigation Helpers,
Buttons, Inputs/Form Controls, Search/Filter, Cards/Containers, Lists, Tables/Data Grid,
Data Display, Charts, Status Elements, Feedback, Modals/Overlays, Menus, Expand/Collapse,
Profile/Entity, Media, Carousel/Paged Content, Map UI, Mobile Specific, Desktop Specific,
Layout, Spatial/Depth, Micro Interaction, Content, Action Groups, Product/Ecommerce,
CRM/Customer, Route/Field Sales, Notifications, AI, Chat, System/App, Interaction States,
Common UX Patterns, and NeginAI Priority Components.
## Priority component set for NeginAI

App Shell · Top Bar · Bottom Navigation · Bottom Dock · Context Bar · Context Strip ·
Search Bar · Segmented Control · Filter Chips · Depth Surface · Layered Panel ·
Bottom Sheet · Floating Panel · Customer Card · Customer 360 · Route Map · Route Stop ·
Visit Workspace · Product Card · Product Detail · Quantity Stepper · Order Draft ·
Order Preview · Commercial Offer · Alert Center · Notification Item · Metric · Progress ·
Status Chip · Next Best Action · AI Insight · AI Recommendation · Skeleton · Loading State ·
Empty State · Error State · Offline State · Sticky CTA · Floating Action · Contextual Action.

## Code ownership

- `vnext/src/design-system/core/` — visual/material/interaction/accessibility primitives.
- `vnext/src/design-system/living/` — semantic living states and motion behavior.
- Product screens consume shared primitives and may add domain layout only.
- Any new screen-specific visual token requires promotion into the Design System or explicit exception.
