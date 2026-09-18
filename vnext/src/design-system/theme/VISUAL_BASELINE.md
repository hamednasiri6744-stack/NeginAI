# NeginAI Visual Baseline v1

This file locks the visual identity approved on 2026-09-18.

## Locked visual language
- Deep near-black navy canvas.
- Cool white primary text with restrained blue-gray secondary text.
- Warm gold is the primary brand/action accent.
- Mint is reserved for live/success state.
- Red is reserved for risk/error state.
- Blue is reserved for information/navigation state.
- Thin low-contrast borders; no bright generic outlines.
- Glass/depth is subtle and dark, never milky.
- Glow is restrained and semantic, not decorative.
- Motion is tactile and quiet.

## Architecture rule
Visual identity and layout are separate concerns.
This theme must remain stable while page layouts may be rebuilt.

## Canonical implementation
- Core tokens: ../core/tokens.css
- Final theme layer: ./visual-baseline.css
- Tailwind aliases: ../../../styles/tailwind.css

Do not introduce a new palette in page-level CSS or JSX.
New UI should consume semantic NeginAI tokens/Tailwind aliases.
