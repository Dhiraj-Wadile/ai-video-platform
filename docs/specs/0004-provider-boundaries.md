# Spec 0004: Provider Boundaries (Capabilities, Router, Normalized Results)

**Phase:** 4 — Boundaries
**Status:** Approved
**Date:** 2026-09-25
**Supersedes parts of:** audit sections 4.4 / 9 ("Boundaries")

## Problem

Provider selection and instantiation are scattered and vendor-specific:

- `VideoPipeline.__init__` hardcodes `OpenAIProvider()`, `PollinationsProvider()`, an
  `ElevenLabsProvider`/`MockVoiceProvider` ternary, and the vendor-specific factory
  `get_video_provider()`.
- There is no shared concept of a **provider capability**, a **configured/enabled** state, or a
  deterministic selection policy (real vs. mock).
- Each raw result type (`LLMResponse`, `ImageResult`, `AudioResult`, `VideoResult`) has no common
  envelope, so downstream code (cost tracking, lineage, Phase 5 Higgsfield, Phase 6) has no single
  boundary to extend.
- The UI cannot enumerate available providers.

This blocks Phase 5 (adapter behind a formal boundary) and Phase 6 (cost/lineage).

## Scope

1. **Capability protocol** — every provider declares `capability` (task type), `name`, `vendor`,
   `models`, `priority`, `is_mock`, and `is_configured()`.
2. **Provider router** — deterministic, policy-driven resolution (skip unconfigured → prefer real
   over mock → lowest priority), plus an inventory API.
3. **Normalized result** — `GenerationResult` envelope + `adapt()` mapper for existing raw results.
4. **Wiring** — the render pipeline consumes the router; new read-only `GET /api/providers`.
5. **Tests + docs** — unit tests for policy/router/adapt and pipeline seam; change log.

**Out of scope (later phases):** Higgsfield adapter (5), persisting cost/lineage to DB (6), UI
screens for provider management (7), provider retries/observability/rate limiting (6/8), routing the
LLM-only API routers (`/api/scripts`, `/api/storyboard`, `/api/trends`, `/api/characters`,
`/api/agents`) through the router (single provider today; zero policy gain).

## Design

### Task types

```python
class ProviderTask(str, Enum):
    LLM = "llm"; IMAGE = "image"; VOICE = "voice"; VIDEO = "video"
    MUSIC = "music"; TRANSCRIPTION = "transcription"
```

### Provider metadata (`app/providers/base.py`)

Add a `ProviderInfoMixin` (non-abstract) with class attributes and a `to_info()` builder:

- `name`, `vendor`, `capability`, `priority` (lower = preferred), `is_mock`, `models`
- `is_configured() -> bool` classmethod (class default `True`)
- `ProviderInfo` dataclass mirrored as `as_dict()` for the API.

Providers become `class XProvider(<ABC>, ProviderInfoMixin)`.

- Real providers are `configured` iff their API key env var is truthy:
  `OpenAIProvider`, `ElevenLabsProvider`, `RunwayVideoProvider`.
- Free/no-key providers are always configured: `PollinationsProvider`, `PollinationsVideoProvider`.
- `MockVoiceProvider` is always configured and `is_mock=True`.

`OpenAIProvider.default_model` moves to a class attribute (still `"gpt-4o"`).

### Router (`app/providers/router.py`)

- `PROVIDER_REGISTRY: Dict[ProviderTask, List[Type]]` — LLM → [OpenAI], IMAGE → [Pollinations],
  VOICE → [ElevenLabs, MockVoice], VIDEO → [Runway, PollinationsVideo].
- `ProviderRouter.resolve(task, name=None)`:
  - explicit `name`: instantiate that class if `is_configured()`, else `ProviderNotConfigured`.
  - policy: `available = [c for c in candidates if c.is_configured()]`; sort by
    `(c.is_mock, c.priority)`; instantiate the head; raise `ProviderNotConfigured` listing
    candidates if none available.
- `available(task)`, `resolve_all()` (LLM/IMAGE/VOICE/VIDEO), `inventory()` / `as_dicts()`.
- **No caching** in the router (stateless → test-friendly); the pipeline caches per instance.
- Module singletons: `provider_router`, `get_provider(task, name=None)`.
- Delete `get_video_provider` (superseded by the router).

### Normalized result

```python
@dataclass
class GenerationResult:
    task: ProviderTask
    provider: str
    model: Optional[str]
    content: str
    media_url: Optional[str]
    audio_base64: Optional[str]
    duration_seconds: Optional[float]
    format: Optional[str]
    latency_ms: int
    cost_cents: int
    usage: dict
    raw: Any
    def as_dict(self) -> dict: ...
```

`adapt(result, task, provider, model=None)` maps `LLMResponse` / `List[ImageResult]` / `AudioResult` /
`VideoResult` → `GenerationResult` (fallback: raw passthrough).

### Pipeline wiring (`app/services/pipeline.py`)

`VideoPipeline.__init__` resolves all providers through the module-level `provider_router`
(`resolve_all()`), drops the direct provider imports, and records a `providers` map in
`PipelineResult.metadata`:

```python
"providers": {
    "llm":   {"name": ..., "model": ...},
    "image": {"name": ...},
    "voice": {"name": ...},
    "video": {"name": ...},
}
```

(name/module fallback `type(instance).__name__`; model via `getattr(instance, "default_model", None)`)

Tests patch the seam `app.services.pipeline.provider_router` with a fake router instead of patching
individual provider classes — so `render`/`generation` tests keep working with zero behavioral
change.

### API

New `app/api/providers.py`: `GET /api/providers` (auth required) → `{"providers": [ProviderInfo.as_dict(), ...]}`.
Registered at `/api/providers` in `app/main.py`.

## Implementation Steps

1. `base.py`: `ProviderTask`, `ProviderInfo`, `ProviderInfoMixin`, `ProviderNotConfigured`,
   `GenerationResult`, `adapt()`.
2. Add metadata + `is_configured()` to: `OpenAIProvider`, `PollinationsProvider`, `ElevenLabsProvider`,
   `MockVoiceProvider`, `PollinationsVideoProvider`, `RunwayVideoProvider`; remove `get_video_provider`.
3. Create `app/providers/router.py`.
4. Rewire `VideoPipeline.__init__` + metadata; remove unused imports (`settings` no longer needed there).
5. Create `app/api/providers.py`; register in `main.py`.
6. Tests: new `tests/test_providers.py`; update the two pipeline-test seams.
7. Run gates (`pytest`, eslint/type-check/test/build), update `docs/changes/0004`, audit row/banner.

## Acceptance Criteria

- `Python`: `ProviderRouter.resolve(VM)`: voice → ElevenLabs when key configured else MockVoice;
  video → Runway when key configured else PollinationsVideo; LLM raises `ProviderNotConfigured`
  when no OpenAI key.
- `inventory()` lists 6 providers with correct task/configured/mock flags; `as_dict()` serializes.
- `adapt()` maps each raw result type into `GenerationResult` with expected fields.
- Pipeline tests pass **without** patching provider classes (only `provider_router`).
- `GET /api/providers` returns the inventory; 401 without auth.
- Both apps' gates are green (backend 25 existing + new tests → all pass).

## Tests to Add

- `test_resolve_prefers_configured_real_over_mock` (voice)
- `test_resolve_config_switch_video` (runway on/off)
- `test_resolve_llm_raises_when_unconfigured`
- `test_resolve_by_name_raises_when_unconfigured`
- `test_inventory_includes_six_providers` (+ flags)
- `test_adapt_llm_image_audio_video`
- `test_providers_endpoint_returns_inventory` (+ 401 unauthenticated)
- `test_pipeline_uses_router_and_records_selection` (fake router → full run → metadata.providers)

## Notes

- `pollinations` is used as `name` by both the image and video free providers — fine because names
  only need uniqueness per task.
- Mock voice returns instantly with empty audio — unchanged behavior.
- No DB/migration changes in this phase (lineage persistence is Phase 6).