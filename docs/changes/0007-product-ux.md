# Change 0007 — Product UX: Scene Studio, Real Data Screens, Dead-Screen Retirement

**Spec:** `docs/specs/0007-product-ux.md`
**Date:** 2026-09-26
**Phase:** 7 — Product UX

## Problem

After Phases 1–6 the backend could produce, persist, regenerate and re-render scenes, but the frontend
did not expose any of it:

- `/studio/editor` was a hand-drawn fake NLE (static timeline, hardcoded "Hook Scene", buttons that did
  nothing, links to nowhere) — the one screen a user needs after generation.
- `/ai/costs`, `/ai/runs` and `/analytics/overview` rendered hardcoded numbers that looked real and were
  fiction (e.g. "Total Runs 170", "$8.42", "45.2K views").
- `/create/new` polled real progress but rendered a fake stage checklist with no percentage or message.
- 11 of 24 screens had no backend at all and were linked from the sidebar.
- The authenticated dashboard was unreachable: `src/app/page.tsx` and `src/app/(dashboard)/page.tsx`
  both resolved to `/`, so the marketing page won and post-login redirect landed on marketing.

## Changes

### Backend

| Change | Why |
|---|---|
| `PATCH /api/projects/{id}/scenes/{scene_id}` | Edit a scene without re-running the pipeline (spec item 1) |
| `GET /api/agents/runs` returns real `GenerationJob` rows | Was a hardcoded `{"runs": [], "total": 0}` stub |
| `GET /api/analytics` scoped to the caller's projects + `videos[]` breakdown | The screen was about to display other tenants' rows; a per-project list is what the UI needs |

Scene PATCH is ownership-checked (project must belong to the caller) and updates only the fields sent
(`exclude_unset`), so a partial edit never blanks untouched columns.

### Frontend

| Screen | Before | After |
|---|---|---|
| `/studio/editor` | fake timeline | Scene Studio: project picker, video preview, quality badge + problems, per-scene thumbnail, debounced inline editing of narration / visual / caption / camera / transition / duration, per-scene **Regenerate visual**, project **Re-render** |
| `/create/new` | stage checklist | real progress bar + `progress_message` + percentage, and lands in the scene studio on success |
| `/content/projects` | non-clickable rows | **Open** button into the scene studio for that project |
| `/ai/runs` | 5 fake rows | real agent runs: agent, model, tokens, latency, cost, error, date |
| `/ai/costs` | fake budget/daily charts | real totals, cost per call, latency, spend-by-project ranked bars |
| `/analytics/overview` | fake 12-month chart | real aggregates, engagement rate, top videos by views |
| `/create/characters` | hardcoded 3 characters + 404 links | list/create (CharacterAgent) + inline edit via the existing endpoints |
| `/create/storyboard` | hardcoded 5 scenes | load a project script or paste one, generate via StoryboardAgent, review the plan |
| `/settings` | fake profile + password boxes for API keys | account summary + live provider status from `GET /api/providers` |

Navigation was reduced to what exists: Discover (Trends), Create (New Video, Script, Characters,
Storyboard), Studio (Scene Editor), Content (Projects), Analytics (Overview), AI (Agents, Runs, Costs).

### Retired (verified static: no `api.` usage, no backend, no unique value)

`/discover/ideas`, `/discover/opportunities`, `/discover/instagram`, `/content/calendar`,
`/content/published`, `/analytics/insights`, `/analytics/videos`, `/ai/models`, `/studio/assets`,
`/studio/audio`, `/studio/captions`.

`/settings` and `/create/{characters,storyboard}` were also static, but a working endpoint existed for
each, so they were wired instead of deleted (the alternative was removing a step of the core journey).

### Route collision fix

`src/app/(dashboard)/page.tsx` → `src/app/(dashboard)/dashboard/page.tsx`. Post-login redirect and the
sidebar logo now target `/dashboard`; `/` is the marketing page only.

### Shared formatting

`lib/utils.ts` gained `formatCost`, `formatCostPrecise`, `formatCount`, `formatMs` (all now used) so
cost/latency/count rendering is defined once instead of inline in four screens, and is unit-tested.

### Tooling

- `npm run lint` → `eslint src` (was `eslint .`, which walked `node_modules` and took >5 minutes).
- `eslint.config.mjs`: global ignores fixed (a config object carrying both `ignores` and `rules` does
  not register global ignores) and `@next/next/no-img-element` disabled — generated media comes from
  provider/storage URLs unknown at build time, so `next/image` cannot be used.

## Verification

- `pytest` — 59 passed.
- `npm run lint`, `npm run type-check`, `npm run test:run` (9 tests), `npm run build` — all green.
- Build now emits 16 routes (was 24 + 3 dead stubs), all backed by a real endpoint.

## Notes / follow-ups

- The render-status endpoint leaks another user's job (fixed in `0008-hardening`).
- No frontend component-render tests: `@testing-library/react` was removed in Phase 2 as unused, and
  re-adding it for two screens is not worth the dependency. Logic that is worth testing lives in
  `lib/utils.ts` and is covered.
- The pipeline itself writes scenes/assets during a render; the storyboard screen shows a *plan*, and
  the studio shows the *persisted* scenes. Merging the two is product work, not a bug.
