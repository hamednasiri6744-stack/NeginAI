# Negin AI Design System v2

Production-oriented, RTL-first visual foundation for the Negin AI React/Vite frontend. The live lab is available at `/design-system`.

## Contract

- Primitive tokens map to semantic tokens and then to component behavior.
- Components are presentation-only. Pricing, tax, stock, credit, route, ERP and KPI semantics remain outside this package.
- All roles share `TopAppBar` + `BottomNavigation`; authorization changes visibility and ordering, not shell architecture.
- Component names and variants map to `NeginAI/<Family>/<Component>/<Variant>` in Figma.
- Touch targets are at least 44px, focus is visible, Persian is primary, and motion respects `prefers-reduced-motion`.

## Design-system-first governance

- Every visual or interaction change starts in the Design System before it reaches a product screen.
- Product screens consume tokens, components and named patterns; they must not introduce one-off visual recipes or page-only theme overrides.
- Reusable screen compositions belong in `patterns/` and must expose a stable React contract.
- Runtime styles are loaded through the single `system.css` entrypoint.
- Theme recipes, component recipes and product patterns must remain separate layers.
- Login is owned by the canonical `AuthPattern`; future authentication visual changes must be made there, not directly in `AuthGate`.
- Figma is the visual design truth; GitHub is the code truth. Approved Figma changes are reconciled into this package before rollout to application routes.
- Legacy CSS may remain temporarily during migration only when unused by the new pattern. It is debt to remove, not a valid extension point.

## Figma mapping metadata

`metadata/registry.json` records families, source paths, target counterpart names, state contract, responsive widths and accessibility requirements. New or revised components and patterns must be reconciled with their Figma counterparts before they are treated as canonical.
