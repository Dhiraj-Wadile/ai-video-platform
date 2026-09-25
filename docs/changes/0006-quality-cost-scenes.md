# Change 0006: Quality, Cost & Scene Regeneration (Phase 6)

**Date:** 2026-09-25
**Phase:** 6 — Quality + cost + scenes
**Spec:** [0006-quality-cost-scenes.md](../specs/0006-quality-cost-scenes.md)
**Status:** Shipped

## Summary

Added structured, persisted quality review (with a gate), per-project and global cost tracking,
persisted scene visuals so single scenes can be regenerated and projects re-rendered from persisted
state, and a unified generation-lineage table.

## Changes

### Data model (migration `004`, `001→002→003→004`)

- `quality_reviews`: `project_id (idx)`, `overall_score`, `breakdown_json`, `problems_json`,
  `recommendations_json`, `safe_to_publish`, `source`, `created_at`.
- `generation_records` (lineage): `project_id (idx)`, `task`, `provider`, `model`, `status`,
  `cost_cents`, `latency_ms`, `parent_id` (chain → regeneration trees), `context_json`, `created_at`.
- `migrations/env.py` now honors `DATABASE_URL` (previously hardcoded to Postgres in `alembic.ini`,
  which made migrations unrunnable against any other DB).

### Structured QA

- `app/services/quality_service.py`: `QualityGate` runs the existing `QualityAgent` against a
  project's script + scenes, persists a `QualityReview`, and gates on
  `overall_score >= settings.qa_threshold` (default 70) **and** `safe_to_publish` — failing marks the
  project `review`.
- Endpoints: `GET /api/projects/{project_id}/quality` (latest review + pass/fail), `POST
  /api/projects/{project_id}/quality/review` (manual trigger; ownership-checked).

### Cost tracking

- `GET /api/projects/{project_id}/costs` aggregates `generation_jobs` (LLM agents) **and**
  `generation_records` (all provider calls) into totals + per-agent/per-task breakdowns.
- `GET /api/costs` (new `app/api/costs.py`) → user-scoped totals + per-project ranked list (multi-user
  isolation verified by test).

### Scene visuals, regeneration & lineage

- Pipeline now persists every generated scene visual as `Asset(type="scene_image")` with
  `metadata_json.scene_id`, and writes chained `generation_records`: `script → storyboard → 1 per
  scene → render(local-ffmpeg)`. (`generation_jobs` for LLM agents is unchanged.)
- `POST /api/projects/{project_id}/scenes/{scene_id}/regenerate` regenerates one scene's visual via
  the router's image provider, uploads a new `scene_image` asset, and records a child lineage record
  whose `parent_id` is the scene's original image record.
- `POST /api/render/recut` (`RecutService`) rebuilds a video purely from persisted scenes + their
  latest visuals (Local-storage path or HTTP download) with word-level captions from the script,
  writing a `RenderJob` and video/captions assets.
- `GET /api/projects/{project_id}/detail` returns the full studio payload (script, scenes with their
  latest image, video url, latest quality review). `GET /api/projects/{project_id}/lineage` returns
  the generation tree newest-first.

## Verification

- `python -m pytest` → **56 passed** (new `tests/test_quality_cost_scenes.py`: QA persist + gate
  fail/pass, ownership isolation, pipeline scene-asset + lineage chaining, project costs aggregation,
  user-scoped global costs, lineage ordering/tree, single-scene regeneration with parent pointer,
  recut producing a completed RenderJob + video asset, foreign-project recut → 404, plus a
  migration-004 upgrade/downgrade unit test mirroring the 003 test).
- `python -c "import app.main"` clean; alembic `DATABASE_URL` override verified by reading env.py.
- The one pre-existing assertion in `test_generation.py` was extended (`video|captions` → also
  `scene_image`) — intentional consequence of persisting scene visuals.

## Notes / Follow-ups

- The baseline migrations (001–003) still use `JSONB`, so the alembic chain is Postgres-only; dev/CI
  run Postgres via Docker. Normalizing those to portable JSON is a Phase 8 hardening item.
- Quality gate is advisory (non-blocking inside the pipeline); wiring blocking behavior into the
  product flow is Phase 7 UX.