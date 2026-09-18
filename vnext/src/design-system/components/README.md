# NeginAI Shared Component Layer

This directory is the operational component layer of the NeginAI Design System.

## Rule

Product screens must compose shared components. They must not create a private visual system for each screen.

Allowed screen CSS:
- page composition and layout
- domain-specific placement
- responsive arrangement unique to that screen

Not allowed in screen CSS:
- redefining button appearance
- redefining segmented controls
- redefining feedback/loading states
- redefining notification item visuals
- redefining live connection indicators
- inventing new color/radius/shadow/motion tokens

## Current canonical components

- Surface
- Button
- SegmentedControl
- LiveIndicator
- FeedbackState
- NotificationItem
- AppHeader
- BottomDock
- StatusChip
- Metric / ProgressBar
- BottomSheet
- EntityHeader
- QuantityStepper
- InsightCard / Next Best Action

Current migrated consumers: Notifications, Home shell/navigation/intelligence, Customer360 shell/navigation/entity states, and Orders quantity control.

## Next shared components

- CustomerCard / Customer360 primitives

Any visual change to a shared component should propagate to every consuming screen.
