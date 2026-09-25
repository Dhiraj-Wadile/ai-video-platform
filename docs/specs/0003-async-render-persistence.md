# Spec 0003 — Async render dispatch + migration standard (Phase 3)

Status: Approved (Phase 3)
Date: 2026-09-25
Spec supersedes the audit's Phase 3 scope: dispatch the existing pipeline via the provisioned
Celery worker, make progress truthful, and standardize on Alembic.

## Problem

1. `POST /api/render/start` runs the entire pipeline (2+ LLM calls → N image fetches → FFmpeg
   render) **synchronously inside the HTTP request**. Production-blocking: a multi-minute request,
   restart kills in-flight work, and the `create/new` UI progress bar is cosmetic (marks every step
   done only after the blocking call returns).
2. Celery + Redis + a `worker` service are **already provisioned** (`docker-compose.yml`,
   `app/tasks/celery_app.py` autodiscovers `app.tasks`) but **nothing ever dispatches**.
3. `app/main.py` lifespan runs `Base.metadata.create_all` on every boot → **Alembic is bypassed**
   in dev/CI; schema drift goes unnoticed.
4. `RenderJob` has no progress-message field; pollers can't see what a running job is doing.

## Goal

- `POST /api/render/start` **enqueues** a Celery task and returns immediately
  (`status: "queued"`) when async is enabled.
- The worker updates the `RenderJob` (status/progress/progress_message/output_url/error) using its
  own DB session, so `GET /api/render/status/{job_id}` returns live, persisted state.
- A deterministic config toggle `RENDER_ASYNC` (default `false`) preserves the current synchronous
  path as a first-class fallback (and keeps tests/SQLite-dev working with zero broker).
- `create_all` removed from app startup; schema managed solely by Alembic.
- Minimal `create/new` change: when the API returns `queued`, poll status and render honest progress
  instead of pretending the video is done.

## Non-goals

- Full-video retry, idempotent redelivery, scene regeneration, generation lineage → **Phase 6**.
- New queues/workers/exchanges/routing → single existing worker.
- Provider normalization, routing, quality, cost → later phases.

## Current behavior

- `POST /api/render/start` → creates `RenderJob(status="rendering")`, runs `VideoPipeline.run`
  inline, returns `status: "completed" | 500 HTTPException`.
- `GET /api/render/status/{job_id}` → returns `job_id, status, progress, output_url`.
- `app/main.py` → `create_all` on startup; no Alembic usage in-app.
- `app/tasks/generation_tasks.py` → 4 Celery tasks, zero dispatch.

## Proposed behavior

### Config
- `config.py`: add `render_async: bool = False` (`RENDER_ASYNC` env).
- `docker-compose.yml`: `api` service env += `RENDER_ASYNC=true`.
- `.env.example`: add `RENDER_ASYNC=false` with comment (dev default).
- `README.md`: document async mode + worker startup.

### New task
- `app/tasks/utils.py`: move `_run_async` from `generation_tasks.py` → `run_async` (same behavior);
  `generation_tasks.py` imports it.
- `app/tasks/render_tasks.py`:
  - `@celery_app.task(bind=True, name="tasks.render_project")` — signature
    `(job_id, project_id, topic, duration, style)`.
  - Opens its own `async_session()`; loads the `RenderJob`; sets `status="rendering"`; runs
    `VideoPipeline.run(..., db=session, on_progress=<async cb>)` where the callback writes
    `progress` + `progress_message` and commits.
  - Marks `completed` (progress 100, `output_url`, `completed_at`) or `failed` (`error`) and commits.
  - Returns `{"status": ...}` dict (result backend is Redis).
  - Task-level auto-retry is explicitly **not** configured (Phase 6 adds safe idempotent retry).

### `app/services/pipeline.py`
- Replace direct synchronous `on_progress(...)` calls with an awaitable helper
  `_emit_progress(on_progress, p, m)` that supports **sync and async callbacks** (worker passes an
  async callback that commits to the DB; API keeps a sync callback).

### `app/api/render.py`
- `POST /api/render/start`:
  - Ownership check + `RenderJob(status="queued")` row as today.
  - If `settings.render_async` → `render_project.delay(job_id, project_id, topic, duration, style)`;
    on broker failure, mark job `failed` and return **500**. Response: `status="queued"`,
    `job_id`, `project_id`, `message="Render queued"`.
  - Else → inline path exactly as today, plus: set `status="rendering"` explicitly, record
    `progress_message` from the progress callback.
- `GET /api/render/status/{job_id}` → response gains `progress_message`.

### `app/main.py`
- Remove `create_all` from lifespan (keep engine disposal). Requires `alembic upgrade head` before
  running; README already prescribes it.

### Migration
- `render_jobs.progress_message String(500)` (`003_add_render_job_progress_message.py`,
  down_revision `002`). Match the model in `app/models/job.py`.

### Frontend (`apps/web/src/app/(dashboard)/create/new/page.tsx`)
- After `startRender` returns `queued` + `job_id`, poll `api.getRenderStatus(job_id)` every 2s
  (max ~10 min). Map `progress_message`/`progress` onto the existing 6-step list
  (thresholds `[0,5,16,31,61,96]`), navigate to `/content/projects` on `completed`, surface the
  error on `failed`, and time out with a clear message. The sync (`completed`) path is unchanged.
- This also activates the previously-unused `getRenderStatus` API client method.

## Architecture impact

No new abstractions, no new infra. The existing Celery worker becomes real; the API becomes a thin
enqueuer in async mode; the pipeline stays the single source of render truth and gets a tiny
callback-upgrade for sync/async progress. Deterministic config switch; no runtime broker detection.

## API/data impact

- `POST /api/render/start`: same request/response shape; `status` is `"queued"` in async mode
  (was `"completed"`), `job_id` still returned. Additive.
- `GET /api/render/status/{job_id}`: additive `progress_message`.
- Writes: `render_jobs.progress_message` column (migration 003). No other schema change.
- `create_all` no longer runs at app startup (Alembic is the only path).

## Risks

- Worker not running + `RENDER_ASYNC=true` → jobs stay `queued`; status endpoint reports honestly,
  README/ops doc covers it. Dev default is `false` so nothing breaks out of the box.
- Async callback committing mid-pipeline shares the session with the pipeline's own writes —
  `expire_on_commit=False` keeps the loaded job mutable across commits (verified with existing
  pipeline persistence tests).
- Celery import cost in the API process (test start uses it) — acceptable.
- Removal of `create_all`: any environment that ran without migrations will be empty until
  `alembic upgrade head` — README/docker-compose already run migrations; documented in the change log.

## Acceptance criteria

- [ ] `pytest -v` → all pass (existing 19 + new).
- [ ] With `RENDER_ASYNC=true`, `POST /api/render/start` returns `"queued"` immediately and the
      `delay()` dispatch receives the expected kwargs (test with a captured fake).
- [ ] The `render_project` task transitions a job `queued → rendering → completed` (or `failed`)
      with `progress_message`, `output_url`, `completed_at`, and persists Script/Scenes/Assets.
- [ ] `GET /api/render/status/{job_id}` includes `progress_message`.
- [ ] Default (`render_async=false`) behavior is byte-for-byte the current sync flow; existing
      render tests pass unchanged.
- [ ] `app.main` no longer executes `create_all`; `python -c "import app.main"` still ok.
- [ ] `alembic upgrade head` produces `render_jobs.progress_message` (Postgres; verified by
      migration unit test for the column ops).
- [ ] Frontend: `npm run lint` / `type-check` / `test:run` / `build` still green.
- [ ] `docs/changes/0003-async-render-persistence.md` documents the change.

## Tests

- `tests/test_generation.py` additions (or `tests/test_render_async.py`):
  1. Async mode enqueues: `monkeypatch settings.render_async=True`, capture `render_project.delay`
     kwargs → response `"queued"`, `RenderJob(status="queued")`, dispatched args correct.
  2. Async mode + broker failure: `delay` raises → job `failed`, HTTP 500.
  3. Task run (call `render_project(...)` synchronously with fake providers/renderer/storage):
     job ends `completed`, `progress=100`, `progress_message` set, `output_url` set; project `ready`.
  4. Task failure: `VideoPipeline` returns `failed` → job `failed` + `error`.
  5. Status response includes `progress_message` (sync path).
  6. Migration 003 ops: `upgrade`/`downgrade` add/drop `render_jobs.progress_message` on a
     SQLite in-memory connection (generic types only).

## Implementation steps

1. `config.py` → `render_async`. 2. `tasks/utils.py` + update `generation_tasks.py`. 3. `tasks/render_tasks.py`.
4. `pipeline.py` → `_emit_progress`. 5. `render.py` → dispatch + progress_message + status field.
6. `models/job.py` + migration 003. 7. `main.py` remove `create_all`. 8. Frontend polling in `create/new`.
9. Env/compose/README updates. 10. Tests. 11. Run all gates. 12. `docs/changes/0003-…`.