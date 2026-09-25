# Change 0004: Provider Boundaries

**Date:** 2026-09-25
**Phase:** 4 (Boundaries)
**Spec:** [0004-provider-boundaries.md](../specs/0004-provider-boundaries.md)
**Status:** Shipped

## Summary

Provider selection and instantiation moved behind a formal boundary: every provider now declares a
capability, vendor, priority, mock flag, and configured state; a deterministic `ProviderRouter`
selects the best enabled provider per task (prefer real → fall back to free/mock → raise); a
normalized `GenerationResult` envelope + `adapt()` mapper unify raw provider outputs; and the render
pipeline consumes the router instead of hardcoding vendors.

## Changes

### Backend boundary layer

- `app/providers/base.py`:
  - `ProviderTask` enum (`llm`, `image`, `voice`, `video`, `music`, `transcription`).
  - `ProviderInfo` dataclass + `as_dict()`; `ProviderInfoMixin` with class-level
    `name`/`vendor`/`capability`/`priority`/`is_mock`/`models` + `is_configured()` + `to_info()`.
  - `ProviderNotConfigured` exception (carries task + candidate names).
  - `GenerationResult` normalized envelope (`as_dict()`) and `adapt(result, task, provider, model)`
    mapping `LLMResponse` / `List[ImageResult]` / `AudioResult` / `VideoResult` (fallback: raw).
- Provider classes updated to declare metadata:
  `OpenAIProvider`, `PollinationsProvider`, `ElevenLabsProvider`, `MockVoiceProvider`,
  `PollinationsVideoProvider`, `RunwayVideoProvider`. Real providers are `configured` iff their API
  key env var is set; `OpenAIProvider.default_model` became a class attribute.
- `app/providers/router.py` (new): `PROVIDER_REGISTRY` (task → provider classes); `ProviderRouter`
  with `resolve(task, name=None)` (policy: configured only → prefer real over mock → lowest
  priority → instantiate; explicit-name lookup + `ProviderNotConfigured`), `resolve_all()`,
  `available()`, `inventory()`, `as_dicts()`; stateless (no caching); module singletons
  `provider_router` and `get_provider()`.
- Removed the superseded vendor factory `get_video_provider()` from `app/providers/video/__init__.py`.

### Pipeline wiring

- `VideoPipeline.__init__` now resolves LLM/IMAGE/VOICE/VIDEO through `provider_router.resolve_all()`
  (imports of provider classes and `settings` removed from the module).
- `PipelineResult.metadata["providers"]` records the resolved provider name + default model per task
  (the seam Phase 6 uses for cost/lineage).

### API

- `app/api/providers.py` (new): authenticated `GET /api/providers` → `{"providers": [...]}`.
- Registered at `/api/providers` in `app/main.py`.

## Verification

- Backend: `python -m pytest -q` → **38 passed** (new `tests/test_providers.py`: resolve policy for
  voice/video, LLM raises `ProviderNotConfigured` when unlocked, resolve-by-name, inventory contents
  + serialization shape, `resolve_all`, `adapt()` for all four raw types, endpoint inventory /
  unauthenticated, pipeline router seam + `metadata.providers`).
- Existing pipeline tests updated to the new seam: they now patch `app.services.pipeline.provider_router`
  (fake router) + `VideoRenderer`/`get_storage` instead of provider classes — zero behavioral change.
- Frontend untouched this phase (gates were green at Phase 3 close).

## Notes / Follow-ups

- LLM still has a single provider and no mock, so `resolve(LLM)` raises a clear error when no OpenAI
  key is configured (the router surfaces this better than the old implicit `AsyncOpenAI()` failure).
- The LLM-only API routers (`/api/scripts`, `/api/storyboard`, `/api/trends`, `/api/characters`,
  `/api/agents`) and the never-dispatched generation tasks keep constructing `OpenAIProvider()`
  directly — routed in a later phase when a second LLM provider exists.
- `resolve_all()` resolves every task by the same policy (so it raises on LLM when unlocked) —
  documented in the spec.