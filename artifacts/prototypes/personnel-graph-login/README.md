# NeginAI Personnel Graph Login Prototype

Standalone visual prototype for a future NeginAI login hero. It is intentionally isolated from the current application and does not modify the existing login flow, backend, authentication, or production data.

## Current scope

- 40+ fake employee nodes across realistic company departments.
- Neutral central nucleus placeholder. The real Negin Pakhsh logo is intentionally not included yet.
- Canvas-based force graph with drag, pan, wheel zoom, touch/pinch zoom and tap focus.
- Double tap/click on a person focuses and zooms into that node.
- Focus mode highlights direct relationships and fades unrelated graph elements.
- Semantic zoom changes information density: department emphasis when zoomed out and person labels when zoomed in.
- Glass-orb personnel nodes, restrained gold lighting, curved links and directional particles.
- Responsive behavior for mobile and desktop.
- Reduced-motion support and an accessible hidden personnel list.
- Fake local data only. No backend/API calls.

## Run

```bash
cd artifacts/prototypes/personnel-graph-login
npm install
npm run dev
```

Open the Vite address shown in the terminal.

## Production build

```bash
npm run build
npm run preview
```

## Prototype controls

- Drag a node to reshape the local graph.
- Drag the background to pan.
- Pinch on touch devices or use the mouse wheel to zoom.
- Tap/click a person to inspect them.
- Double tap/click the same person to focus and zoom.
- Tap/click the empty background to clear focus.
- Flow, Labels and Motion can be toggled from the small control dock.
- Reset returns to the central organization view.

## Architecture notes

The first version deliberately uses `react-force-graph-2d` rather than a DOM-heavy graph. Rendering stays on Canvas so the design can scale to a larger personnel graph while preserving touch interaction and animated links. The personnel card and controls are the only primary DOM overlays.

The center node is fixed at graph coordinates `(0, 0)`. When the visual language and interaction are approved, the Negin Pakhsh logo can replace the neutral nucleus without changing the graph model.

## Next refinement targets

1. Replace fake personnel data with an approved privacy-safe personnel projection after authentication rules are defined.
2. Add the exact Negin Pakhsh logo as the graph nucleus.
3. Tune department clustering and force parameters against the real organization size.
4. Add optional avatar textures only if public-login privacy requirements allow them.
5. Integrate the approved graph layer into the existing login page only after visual and performance QA.

## Safety boundary

This prototype does not read or write production data, does not call Varanegar or NeginAI APIs, and does not alter the existing product login implementation.
