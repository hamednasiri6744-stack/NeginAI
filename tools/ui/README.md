# NeginAI UI/UX Quality Harness - Wave 1B

This harness adds engineering checks around the existing NeginAI UI without redesigning the product shell, changing its colors, or replacing its business semantics.

## Gating checks

- npm run ui:types - validates the TypeScript-based UI tooling configuration.
- npm run ui:e2e - runs Playwright on Chromium desktop and a mobile Chrome device profile.
- npm run ui:check - runs the green Wave 1B gate (ui:types + ui:e2e).

The Playwright runner first checks /health, then tests /assistant against NEGINAI_UI_BASE_URL (default http://127.0.0.1:8001).

## Extended checks

- npm run ui:e2e:cross - all configured Chromium, Firefox and WebKit desktop/mobile projects.
- npm run ui:e2e:headed - default Chromium profiles in headed mode.
- npm run ui:perf - Lighthouse HTML/JSON artifacts under artifacts/ui/lighthouse.
- npm run ui:lint:js and npm run ui:lint:css - strict legacy-code debt reports.

## Legacy lint debt

Strict linters intentionally remain non-gating in Wave 1B because the pre-existing monolithic UI contains substantial technical debt. The first strict scan on 2026-09-04 reported:

- JavaScript: 42 errors and 49 warnings.
- CSS: 3,888 errors under the newly introduced standard Stylelint rules.

Wave 1B does not mass-rewrite the 465 KB JavaScript or 141 KB CSS merely to satisfy formatting rules. Later waves should reduce these findings incrementally while preserving behavior and visual identity.
