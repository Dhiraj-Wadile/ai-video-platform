# Change 0003: Async Render Dispatch + Persistence

**Date:** 2026-09-25
**Phase:** 3 (Async + Persistence)
**Spec:** [doc/specs/0003-async-render-persistence.md](../specs/0003-async-render-persistence.md)
**Status:** Shipped

## Summary

Renders can now be dispatched asynchronously to a Celery worker instead of blocking the API
request. A `RENDER_ASYNC` setting switch preserves the deterministic synchronous path used by
tests and local development. Job status/progress/failure is persisted to `render_jobs` and
exposed over the existing status endpoint.

## Changes

### Backend

- `app/config.py`: added `render_async: bool = False` (`RENDER_ASYNC` env).
- `app/api/render.py`:
  - async mode: `POST /api/render/start` creates a `queued` `RenderJob`, enqueues
    `render_project.delay(...)`, and returns `{status: "queued", job_id, message}`; a broker
    failure marks the job `failed` and raises HTTP 500.
  - sync mode (unchanged contract): job is set to `rendering` up front and now records
    `progress_message` at every step; on success it is `completed` with `progress_message`.
  - `GET /api/render/status/{job_id}` now returns `progress_message` and `error`.
- `app/tasks/utils.py` (new): `run_async()` helper — runs a coroutine in a fresh worker thread if an
  event loop is already running, otherwise `asyncio.run()`.
- `app/tasks/generation_tasks.py`: switched to the shared `run_async`.
- `app/tasks/render_tasks.py` (new): `render_project` bound Celery task. Opens its own
  `async_session`, marks the job `rendering`, runs the pipeline with an **async** progress callback
  that commits `progress`/`progress_message` after each step, then `completed`
  (`output_url`, `completed_at`) or `failed` (`error`).
- `app/services/pipeline.py`: extracted `_emit_progress` (unifies sync + async callbacks) and
  awaited it at every pipeline step; renderer progress is bridged via an async closure that maps
  renderer progress into the 60–95 range.
- `app/services/render_service.py`: same `_emit_progress` pattern.
- `app/models/job.py`: `RenderJob` gains `progress_message` (String 500).
- `migrations/versions/003_add_render_job_progress_message.py` (new): add/drop
  `render_jobs.progress_message`. Uses generic `sa.String` so it is portable (also covers SQLite).
- `app/main.py`: removed `Base.metadata.create_all` from the lifespan — schema is Alembic-managed
  only (tests keep using conftest `create_all`).

### Frontend

- `create/new/page.tsx`: when `/api/render/start` returns `queued`, polls
  `getRenderStatus(job_id)` every 2s (up to ~10 min) and maps real progress onto the six-step UI
  via thresholds `[0, 5, 16, 31, 61, 96]`; navigates on `completed`, surfaces `error` on `failed`.
  This activates the previously unused `api.getRenderStatus`.

### Config / Docs

- `.env.example`: documented `RENDER_ASYNC=false`.
- `docker-compose.yml`: API service sets `RENDER_ASYNC=true`.
- `README.md`: async-render section (worker + polling) and note that schema is Alembic-only.

## Verification

- Backend: `python -m pytest -q` → **25 passed** (new tests cover async enqueue, enqueue-failure
  → job failed + 500, task success → job `completed` with `progress_message`/`output_url`, task
  failure → `failed` + `error`, status response fields, migration 003 up/down on SQLite).
- Frontend: `eslint` 0 errors, `tsc --noEmit` pass, `vitest run` 1 passed, `next build` pass.
- Existing `test_generation.py` fake renderer updated to await the async progress callback.

## Notes / Follow-ups

- No task auto-retry or dedicated queues yet (scoped to Phase 6).
- Confirmed by experiment that bound Celery tasks execute eagerly via `task(...)` / `task.run(...)`,
  which is how the worker logic is unit-tested.
- Node audit still reports transitive vulnerabilities (pre-existing, out of scope).