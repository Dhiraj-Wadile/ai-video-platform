# Spec 0007: Product UX — Studio, Progress Clarity, Dead Screens (Phase 7)

**Status:** Approved
**Phase:** 7 — Product UX

## Objective

Make the frontend reflect the now-functional backend: a real scene studio (view, edit, regenerate,
re-render), honest progress during generation, live data on the AI Costs / AI Runs / Analytics
screens, and retirement of dead static placeholder screens that burden the nav.

## Non-goals

- No timeline scrubber / frame-accurate NLE editing (out of product scope).
- No new design system or routing overhaul.
- No backend voice/live caption wiring.

## Design

### 1. Backend additions

- `PATCH /api/projects/{project_id}/scenes/{scene_id}` — ownership-checked partial update of scene
  fields (`duration`, `narration`, `visual_description`, `camera`, `emotion`, `background`,
  `music_mood`, `sfx`, `caption`, `transition`). Returns the updated scene.
- `GET /api/agents/runs` — currently a stub returning `{"runs": [], "total": 0}`; replace with the
  real agent runs (`GenerationJob` rows across the user's projects, newest first, limited) so the AI
  Runs screen shows real data.

### 2. Studio editor (`/studio/editor`)

Rebuild as a functional scene studio:
- Project picker (list from `/api/projects`) → loads `/api/projects/{id}/detail`.
- Scene list: each scene shows its current `scene_image` thumbnail, number, narration, caption, and
  status indicators. Inline editing of key fields via the new PATCH endpoint (debounced save).
- Per-scene **Regenerate visual** button → `POST .../scenes/{scene_id}/regenerate`, then refresh
  detail.
- **Re-render** button → `POST /api/render/recut`, then refresh; surfaces the resulting `job_id` /
  video URL.
- Video preview: show the project's `video_url` when available.
- Quality badge from `detail.quality` (score + passed/failed).

### 3. Progress clarity (`/create/new`)

Async polling already returns `progress` + `progress_message`. Surface both: a real percentage bar
and the live last `progress_message` text while stages tick over.

### 4. Wire up static-but-real screens

- `/ai/costs` → `GET /api/costs` (totals + per-project ranked list).
- `/ai/runs` → `GET /api/agents/runs` (now real).
- `/analytics/overview` → `GET /api/analytics` (aggregate metrics cards).

### 5. Retire dead static screens

Delete page files + nav entries for screens with no backend and no unique value:
`/discover/ideas`, `/discover/opportunities`, `/discover/instagram` (Discover → Trends only),
`/content/calendar`, `/content/published`, `/analytics/insights`, `/analytics/videos`,
`/ai/models`. Confirmed static (no `api.` usage), removing maintenance drag without touching the
core journey.

## Acceptance / tests

Backend:
1. Scene PATCH persists edits and enforces ownership (foreign user → 404; unknown scene → 404).
2. `/api/agents/runs` returns real GenerationJobs for the user's projects only (multi-user
   isolation), newest first, shape `{runs, total}`.

Frontend (build/lint/type-check/test:run must stay green):
3. `/studio/editor` renders a project's scenes from `/detail` with editable fields, regenerate and
   re-render actions, and the video preview area.
4. `/create/new` shows live `progress` bar + `progress_message`.
5. `/ai/costs`, `/ai/runs`, `/analytics/overview` render server data.
6. Retired routes no longer render nav links; removed page files.

## Verification

- Backend: `python -m pytest` green.
- Web: `npm run lint`, `npm run type-check`, `npm run test:run`, `npm run build` green (in `apps/web`).
- Docs: `docs/changes/0007-product-ux.md`; audit row 7 → done.

## Out of scope (later)

- Blocking quality gates in the UI flow, MCP server, NLE editor.