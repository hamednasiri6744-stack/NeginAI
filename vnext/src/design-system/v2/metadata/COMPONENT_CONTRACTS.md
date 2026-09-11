# Component mapping contracts

All components inherit `default`, `hover`, `focus-visible`, `active`, and `disabled` where interactive. Status-bearing components use text/icon plus color. Every interactive target is at least 44px, Persian labels are primary, and logical CSS properties define RTL behavior. Figma counterpart status is `FIGMA_MAPPING_PENDING` until a separate approved synchronization pass.

| Component | Token dependencies | Variants / states | Responsive behavior | Accessibility contract | Source | Figma counterpart |
|---|---|---|---|---|---|---|
| Button | action, text-inverse, radius-button, focus, motion | primary, secondary, ghost, destructive; loading, success, warning, error, offline | labels may wrap; full-width is consumer controlled | native button, busy and disabled semantics, visible focus | `components/actions.tsx` | `NeginAI/Actions/Button/*` |
| IconButton / FAB | action, touch, radius-floating | default, premium, destructive; disabled | FAB label remains readable on narrow screens | required accessible name, 44px target | `components/actions.tsx` | `NeginAI/Actions/IconButton/*` |
| Field / inputs | field-bg, border, focus, danger | normal, required, disabled, invalid; input-specific types | form grids collapse from 2/3 columns to one | persistent label, described help/error, invalid state | `components/forms.tsx` | `NeginAI/Forms/*` |
| Choice controls | surface, accent, touch | checked, unchecked, disabled | natural wrapping | native checkbox/radio semantics; switch exposes role and checked state | `components/forms.tsx` | `NeginAI/Forms/Choice/*` |
| Feedback states | semantic status colors, border, text | neutral, premium, info, success, warning, danger, offline | states stack in narrow containers | icon plus text, alert/status live-region semantics | `components/feedback.tsx` | `NeginAI/Feedback/*` |
| Card / MetricCard | card-bg, surface elevation, numeric typography | static, interactive; semantic trend tone | metric grids become one column | semantic article and legible tabular numerals | `components/data.tsx` | `NeginAI/Data/Card/*` |
| Table | surface, border, body-sm, numeric | regular, dense, responsive | table becomes labeled data cards below 768px | caption, scoped headings, keyboard-focusable scroll region | `components/data.tsx` | `NeginAI/Data/Table/*` |
| Tabs | surface, accent, focus, touch | underline, segmented; selected, disabled | horizontally scrollable tab list | tablist pattern, roving tab index, RTL arrow behavior | `components/navigation.tsx` | `NeginAI/Navigation/Tabs/*` |
| BottomNavigation | navigation-bg, nav elevation, safe area | active, center AI emphasis | fixed full width on mobile; floating bounded rail from 768px | navigation landmark, current-page state, text labels | `components/navigation.tsx` | `NeginAI/Navigation/BottomNavigation/*` |
| Modal / Sheet / Drawer | overlay, glass-strong, modal elevation, motion | modal, bottom sheet, app drawer; open/closed | mobile task flows favor sheet; dialog remains bounded | native dialog, Escape/cancel, labeled close | `components/navigation.tsx` | `NeginAI/Navigation/Overlay/*` |
| AIComposer / response | ai-surface-bg, info, focus, floating radius | idle, streaming/loading, attachment/tool result | actions remain wrapped and touch-safe | labeled composer/actions, busy status is textual | `components/ai.tsx` | `NeginAI/AI/*` |
| MasterDetail | surface, border, content width | master/detail | collapses to stacked flow below 768px | source order remains meaningful | `patterns/index.tsx` | `NeginAI/Patterns/Enterprise/MasterDetail` |
| Seller presentation | card, status, touch, responsive grid | presentation-only | cards and rows reflow without changing semantics | status text, named actions, no color-only meaning | `patterns/index.tsx` | `NeginAI/Patterns/Operational/*` |

The complete inventory and source mapping are machine-readable in `registry.json`.
