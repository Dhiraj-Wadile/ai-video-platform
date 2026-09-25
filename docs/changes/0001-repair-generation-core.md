# Change 0001 — Repair the broken generation core

Date: 2026-09-25 · Phase 1 · Spec: `docs/specs/0001-repair-generation-core.md`

## What changed

### Backend
- **`app/agents/base.py`** — `BaseAgent.run()` now accepts `AgentInput | dict` and normalizes a dict to
  `AgentInput`. All existing call sites (routers, pipeline, tasks) now work; the dataclass contract is
  still the internal type. Removed unused `import uuid`.
- **`app/api/scripts.py`** — `POST /api/scripts/generate` accepts optional `project_id` (ownership
  validated), persists a `Script` row and sets `Project.status = "generating"` when provided; response
  gains `id`. Dropped unused `Scene` import.
- **`app/services/pipeline.py`** — `run()` gains optional `db: AsyncSession`. When provided the pipeline
  tracks `Project.status` (`generating` → `ready`/`failed`) and persists:
  - `Script` (title, content, duration, structure_json),
  - `Scene` per storyboard entry,
  - `GenerationJob` per agent call (model, tokens, latency, cost),
  - `Asset(type="video" | "captions")`.
  Fixed unawaited `storage.get_url()`.
- **`app/api/render.py`** — `POST /api/render/start` persists a `RenderJob` (`status="rendering"`),
  updates progress via the pipeline callback, marks `completed`/`failed` (with `error` stored), returns
  `job_id`. `GET /api/render/status/{job_id}` now reads the string `status` directly (no `.value` crash)
  and enforces project ownership on start.
- **`app/models/job.py` + `migrations/versions/002_add_render_job_error.py`** — added `render_jobs.error`
  column (migration `002`, down-revision `001`).

### Tests
- Added `tests/test_agents.py` (4 tests: dict normalization, missing-context defaults, dataclass input,
  non-JSON resilience).
- Added `tests/test_generation.py` (7 tests: script persistence, no-project path, foreign-project 403/404,
  full pipeline persistence via mocked providers/renderer/storage incl. Script/Scenes/GenerationJobs/Assets
  + project status, render-job failure marking, status endpoint, render ownership).

## Verification
- `pytest -v` → **19 passed** (was 8).
- `python -c "import app.main"` and `py_compile` on all touched files → OK.

## Compatibility
- `POST /api/render/start` and `POST /api/scripts/generate` responses are additive (`job_id`, `id`).
- No existing frontend call is broken; `startRender` still returns `status/project_id/message`.