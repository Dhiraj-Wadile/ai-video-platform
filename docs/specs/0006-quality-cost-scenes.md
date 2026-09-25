# Spec 0006: Quality, Cost & Scene Regeneration (Phase 6)

**Status:** Approved
**Phase:** 6 — Quality + cost + scenes

## Objective

Close the "generation fidelity" gaps flagged in the audit: make quality review structured and
persisted, track per-project generation cost, persist scene visuals so a single scene can be
regenerated without rerunning the whole pipeline, and expose a unified generation lineage.

## Non-goals

- No auto-gating of the pipeline on quality (advisory gate only; wiring into blocking flows is Phase 7
  UX territory).
- No voice/music provider invocation (unchanged from current product scope).
- No cost estimation for local FFmpeg renders (zero API cost by nature).
- No S3/MinIO transport in tests beyond the existing storage seam.

## Design

### 1. Structured QA (persisted QualityReview + QualityGate)

- New table `quality_reviews`: `id, project_id (idx), overall_score int, breakdown_json,
  problems_json, recommendations_json, safe_to_publish bool, source str(20) ("pipeline"|"manual"),
  created_at`.
- `app/services/quality_service.py::QualityGate.review(project_id, script, scenes, db)`:
  runs the existing `QualityAgent`, persists a `QualityReview`, applies the threshold gate
  (`settings.qa_threshold`, default 70): passes when `overall_score >= threshold` and
  `safe_to_publish`; when failing, sets `project.status = "review"`.
- `app/config.py`: `qa_threshold: int = 70`.
- Endpoints (project-scoped, ownership-checked): `POST .../quality/review`, `GET .../quality`.

### 2. Cost tracking

- Pipeline already persists `GenerationJob` (LLM: script/storyboard) with `cost_cents`, `tokens_*`,
  `latency_ms`. This phase captures image-generation cost too via the new lineage table (below).
- `GET /api/projects/{project_id}/costs` → aggregate over `generation_jobs` **and**
  `generation_records`: `total_cost_cents`, `total_latency_ms`, `task_breakdown`, `agent_breakdown`.
- `GET /api/costs` (new `app/api/costs.py`, prefix `/api/costs`) → user-wide sums across their
  projects plus a per-project list.
- `GET /api/projects/{project_id}/lineage` → all `generation_records` for the project (newest first).

### 3. Scene visuals persisted + regeneration

- Pipeline now persists each generated scene visual as `Asset(type="scene_image")` with
  `metadata_json = {"scene_id": <int>, "source": "pipeline"}`. Studio/recut use these.
- `POST /api/projects/{project_id}/scenes/{scene_id}/regenerate`:
  - ownership-checked; resolves the scene via its `scene_number`.
  - regenerates the visual through `provider_router.resolve(ProviderTask.IMAGE)` using
    `visual_description`; uploads to storage; creates a new `Asset(type="scene_image")` with
    `metadata_json = {"scene_id", "source": "regenerate", "regenerated": true}`.
  - writes a `GenerationRecord` child whose `parent_id` is the scene's original image record.
  - returns `{ scene, asset_url, record_id }`.

### 4. Generation lineage

- New table `generation_records`: `id, project_id (idx), task str(30), provider str(50), model
  str(100), status str(20), cost_cents int, latency_ms int, parent_id str(36) nullable,
  context_json JSON, created_at`.
- Pipeline writes one record per provider call (script → storyboard → each scene image), chained via
  `parent_id`. This is additive: `generation_jobs` (LLM/agents) is untouched. One existing test
  assertion about asset types grows to include `scene_image`.
- Regeneration appends a child record → tree shows the regeneration chain.

### 5. Re-render from persisted scenes (`POST /api/render/recut`)

- `app/services/recut_service.py::RecutService.recut(project_id, db)`:
  loads scenes ordered by `scene_number`, resolves each scene's **latest** `scene_image` asset to a
  local file (Local-storage path or HTTP download), derives captions from the script word-level,
  renders via `VideoRenderer`, uploads the video and persists a `scene_image`-independent
  `Asset(type="video")` + a completed `RenderJob`.
- Endpoint body `{project_id}`; ownership-checked; returns `{job_id, status, output_url}`.
- Renderer/storage remain seams (patched in tests exactly like the pipeline render).

## Acceptance / tests (new `tests/test_quality_cost_scenes.py` + minor updates)

1. Quality review persists a `QualityReview` and sets project status to `review` when score < threshold.
2. Passing review leaves/returns project to gate-passed state.
3. `GET .../quality` returns the latest review + gate result; ownership enforced.
4. Pipeline run persists: scenes → `scene_image` assets AND `generation_records` chain
   (script→storyboard→1 per scene) [update the one asset-type assertion in `test_generation.py`].
5. `GET .../costs` aggregates LLM + image generation cost correctly.
6. `GET /api/costs` returns user-scoped sums (multi-user isolation).
7. `GET .../lineage` returns records newest-first with parent pointers.
8. Scene regeneration produces a new scene_image asset, a child lineage record (parent = scene's
   original image record), and a 200 with asset URL.
9. Recut: given persisted scenes + scene_image assets, produces a RenderJob (completed, output_url)
   and a video Asset; foreign-project recut → 404.
10. Unauthorized access to any new endpoint → 401/403.

## Verification

- `python -m pytest -q` green (existing 45 + new), plus `python -c "import app.main"` smoke.
- Docs: `docs/changes/0006-quality-cost-scenes.md`; audit row 6 → done.

## Out of scope (later phases)

- Blocking quality gates in pipeline, studio editing UI for scenes (Phase 7), CI security hardening
  (Phase 8).