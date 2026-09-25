# Spec 0001 — Repair the broken generation core (Phase 1)

Status: Approved (Phase 1)
Date: 2026-09-25

## Problem

The primary product journey ("give me an idea → the platform produces a video") is broken at
runtime. Every agent call site passes a plain `dict` to `BaseAgent.run()`, which requires the
`AgentInput` dataclass and accesses `input.content` / `input.context` as attributes. This raises
`AttributeError` on `POST /api/scripts/generate`, `POST /api/storyboard/generate`,
`POST /api/trends/analyze`, `POST /api/agents/{name}/run`, `POST /api/characters`, and — critically —
`POST /api/render/start` (the whole pipeline). Additionally:

- Scripts, scenes, assets and render jobs are never persisted — the pipeline leaves no trace.
- `GET /api/render/status/{job_id}` crashes on `job.status.value` where `status` is a `String` column.
- Project status never transitions from `draft`.

## Goal

A logged-in user can create a project, generate a video **synchronously** through the existing
pipeline, and observe a persisted, truthful result: Script + Scenes + video Asset + RenderJob rows,
correct project-status transitions, and a working status endpoint.

## Non-goals (later phases)

- Async/Celery dispatch, real progress polling, scene regeneration, quality/cost, provider routing,
  Higgsfield, frontend rework. This phase only makes the existing synchronous flow *work and persist*.

## Current behavior

- Agent endpoints raise `AttributeError` (uncaught; no tests cover agents).
- `RenderJob` rows are never created; `GET /api/render/status` returns `"unknown"` or crashes.
- Pipeline produces an mp4 to disk but never records it in the DB.

## Proposed behavior

1. `BaseAgent.run()` accepts `AgentInput | dict` — normalizes a dict to `AgentInput`. All 8 existing
   call sites keep working unchanged.
2. `POST /api/scripts/generate` optionally accepts `project_id`; when provided, persists a `Script`
   row (validated to belong to the caller) and returns its `id`.
3. `POST /api/render/start`:
   - Creates and persists a `RenderJob` (`status="rendering"`) before running the pipeline.
   - Runs `VideoPipeline.run(...)` with a DB session.
   - On success sets `status="completed"`, `progress=100`, `output_url`, `completed_at`.
   - On failure sets `status="failed"`, `error`.
   - Adds `job_id` to the response (existing keys unchanged).
4. `VideoPipeline.run()` gains an optional `db` session parameter. When present it:
   - Sets `Project.status = "generating"` at start.
   - Persists the generated `Script`.
   - Persists each `Scene`.
   - Records a `GenerationJob` per agent call (traceability, model/tokens/cost from agent metadata).
   - Persists the rendered video as an `Asset(type="video")` and the SRT as `Asset(type="captions")`.
   - Transitions `Project.status` to `"ready"` on success or `"failed"` on error.
5. `GET /api/render/status/{job_id}` reads `job.status` directly (string) — no `.value` crash.

## Architecture impact

Minimal, no new abstractions. `VideoPipeline` gains a single optional dependency (DB session).
Agent contract stays a dataclass internally; dict input is normalized at the boundary.

## API/data impact

- `POST /api/scripts/generate` — additive optional `project_id`; response gains `id`.
- `POST /api/render/start` — response gains `job_id`; existing `status/project_id/message` unchanged.
- Writes: `scripts`, `scenes`, `generation_jobs`, `render_jobs`, `assets` rows now created.
- No migration changes (all tables already exist in `001_initial`).

## Risks

- Pipeline relies on OpenAI + Pollinations + FFmpeg at runtime (unchanged from today); failures
  are caught and recorded as `PipelineResult(status="failed")` → job/status marked failed, 500 to client.
- Guard all persistence behind `if db is not None` so the pipeline stays usable without a session.

## Acceptance criteria

- [ ] Agent unit tests: `ScriptAgent.run({"content": ...})` returns structured data (no AttributeError).
- [ ] `POST /api/scripts/generate` with `project_id` persists a `Script` and returns its `id`.
- [ ] `POST /api/render/start` creates a `RenderJob`; success → `status=completed`, project `ready`, video `Asset` row present.
- [ ] `GET /api/render/status/{job_id}` returns the persisted job without error.
- [ ] Existing 8 tests still pass.

## Tests

- `tests/test_agents.py` — unit tests with a fake `LLMProvider` (dict input normalization, structured JSON parse).
- `tests/test_generation.py` — endpoint tests monkeypatching `OpenAIProvider` (scripts) and `VideoPipeline` (render), covering script persistence, render job lifecycle, project status, and status endpoint.

## Implementation steps

1. `agents/base.py` — normalize `AgentInput | dict` in `run()`.
2. `api/scripts.py` — optional `project_id`, persist `Script`.
3. `services/pipeline.py` — optional `db`; persist Script/Scenes/GenerationJobs/Assets; manage project status.
4. `api/render.py` — `RenderJob` lifecycle; fix status endpoint; `job_id` in response.
5. Add tests; run `pytest -v`.
6. Update `docs/changes/` log.