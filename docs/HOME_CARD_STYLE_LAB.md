# Home Card Style Lab

Purpose: keep the current Home card structure/content fixed and test visual styles on the exact same cards, reversibly.

## Frozen structure
- Card 1: date/time/work-calendar; static, not clickable.
- Card 2: monthly target; clickable shell only, second layer intentionally empty.
- Card 3: target-to-today; clickable shell only, second layer intentionally empty.
- Card 4: required sales to month-end; clickable shell only, second layer intentionally empty.
- No corner-arrow affordance on cards.
- Typography/content/data wiring stay fixed during surface-style tests.
- Backend and semantic logic must not change during these tests.

## Control
Active style is selected by one constant in:
`vnext/src/components/VisitorHomeScreen.tsx`

`HOME_CARD_STYLE`

Baseline checkpoint:
`checkpoint/home-card-style-lab-baseline-20260919`

Current baseline style:
`glass-neu` = dark Glassmorphism + Neumorphism.

Active test style:
pure-glass = translucent glass surface with stronger blur/refraction and no neumorphic dual-shadow depth.
## Style test queue
- [x] Glassmorphism + Neumorphism baseline
- [x] Pure Glassmorphism
- [x] Frosted Glass — active test
- [ ] Liquid Glass
- [ ] Layered Glass
- [ ] Acrylic
- [ ] Pure Neumorphism
- [ ] Dark Neumorphism
- [ ] Soft UI
- [ ] Claymorphism
- [ ] Tactile / Physical UI
- [ ] Skeuomorphism
- [ ] Material-style surface
- [ ] Fluent-style surface
- [ ] Matte surface
- [ ] Glossy surface
- [ ] Metallic surface
- [ ] Translucent minimal surface
- [ ] Flat minimal
- [ ] Neo-Brutalist card
- [ ] Organic / Biomorphic card
- [ ] Tech Minimal
- [ ] Premium / Luxury
- [ ] Calm Futurism
- [ ] Cyber / Futuristic

## Test rule
Each style gets its own reversible commit/checkpoint. Only surface treatment, depth, border, radius, shadow, blur, highlight, refraction and press feedback may change unless explicitly requested.



## Live switcher
- 25 styles are now available from the temporary Style button on Home.
- Switching is instant in-browser; no rebuild/redeploy is required between styles.
- The selected style persists in localStorage for comparison across refreshes.
- This is a temporary test control and can be removed once a final surface style is selected.


## Dynamic styles
- [x] Aurora Glass
- [x] Living Liquid
- [x] Breathing Neumorphism
- [x] Shimmer Metal
- [x] Reactive Luxury
- [x] Live intensity control 0-100
- [x] Intensity persisted in localStorage
- [x] Reduced-motion safety disables animation

