# Negin AI Design System v2

Production-oriented, RTL-first visual foundation for the Negin AI React/Vite frontend. The live lab is available at `/design-system`.

## Contract

- Primitive tokens map to semantic tokens and then to component behavior.
- Components are presentation-only. Pricing, tax, stock, credit, route, ERP and KPI semantics remain outside this package.
- All roles share `TopAppBar` + `BottomNavigation`; authorization changes visibility and ordering, not shell architecture.
- Component names and variants map to `NeginAI/<Family>/<Component>/<Variant>` in a future Figma pass.
- Touch targets are at least 44px, focus is visible, Persian is primary, and motion respects `prefers-reduced-motion`.

## Figma mapping metadata

`metadata/registry.json` records families, source paths, target counterpart names, state contract, responsive widths and accessibility requirements. Figma mutation is intentionally deferred until runtime visual review.
