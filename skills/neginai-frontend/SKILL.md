---
name: neginai-frontend
description: "NeginAI React TypeScript Vite frontend routing API query state forms validation PWA architecture. فرانت اند ری اکت تایپ اسکریپت روتینگ فرم API"
---
# NeginAI Frontend
Target: D:\\Projects\\NeginAI\\vnext. Architecture: Backend/API Contracts -> Data Layer -> Domain Features -> Reusable Components -> Design System -> Responsive/Mobile/PWA -> Visual QA. Use React + TypeScript + Vite, real routing, typed API client, server-state/query, forms/validation, auth/role visibility, error/loading/empty/offline states, reusable primitives and tests. Never reimplement Varanegar business semantics in React. Inspect git status/diff before edits; unknown dirty files belong to other work.

## UI Iteration Performance
Use Vite HMR on a dedicated fast-preview port for day-to-day UI iteration. Keep the stable public preview separate. Do not run tsc+vite production build for each cosmetic edit; run build/lint/tests at meaningful checkpoints. Prefer one coherent component patch over many sequential shell edits.
