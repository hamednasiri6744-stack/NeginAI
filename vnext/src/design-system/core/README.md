# NeginAI Design System Atlas v1

Canonical code layer derived from the approved Design System Atlas.

## Direction

- Spatial Enterprise Neo
- Premium Enterprise + Calm Futurism
- Layered / tactile glass
- App-like, workflow-first, anti-dashboard
- Depth-first information architecture
- Living UI as semantic state behavior
- Mobile-first RTL
- Accessibility and performance are part of the design contract

## Surface grammar

`Stage -> Surface -> Detail -> Floating / Sheet`

Prefer connected surfaces and progressive disclosure over card-everywhere layouts.
## Core rules

- Gold is an accent/action color, not a wallpaper color.
- Glass is used for hierarchy and continuity, not decoration.
- Neumorphic/tactile treatment is reserved for interactive controls.
- Motion must communicate state, data change, continuity or feedback.
- Every interactive control supports focus, pressed and disabled behavior.
- Numeric/technical content may use isolated LTR inside the RTL shell.
- Touch targets default to at least 44px.
- Reduced-motion is mandatory.
- Product screens consume shared tokens/primitives; they do not invent local design systems.

## Relationship to Living UI

`core/` defines visual/material/interaction primitives.
`living/` defines semantic motion and live-state behavior.
The two layers are complementary and should not duplicate tokens.
