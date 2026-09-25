# Spec 0005: Higgsfield Video Provider (official SDK adapter)

**Phase:** 5 — Higgsfield
**Status:** Approved
**Date:** 2026-09-25
**Research base:** official docs at https://docs.higgsfield.ai (llms.txt, Client libraries, Requests and
lifecycle, File uploads, API reference) and https://github.com/higgsfield-ai/higgsfield-client (README).
Verified 2026-09-25.

## Problem

There is no first-class video-generation provider that uses real AI-video models. Today the video
capability resolves to Runway (when keyed) or a free Pollinations URL stub that the pipeline never
calls. Phase 4 built the provider boundary; this phase installs a real, documented video adapter
behind it so the platform can generate actual AI video via Higgsfield's one-API-for-many-models
service.

## Facts established from current official docs

- **Python SDK:** `pip install higgsfield-client` (Python 3.8+, Apache-2.0). Async entry points used
  here: `higgsfield_client.subscribe_async(model, arguments={...})` (submit + poll + wait) and
  `higgsfield_client.upload_async(data, content_type)` (not needed — inputs accept public HTTPS URLs).
- **Credentials:** `export HF_KEY="key-id:key-secret"` (or `HF_API_KEY` + `HF_API_SECRET`). Auth header
  `Authorization: Key <ID>:<SECRET>` handled by the SDK.
- **Model endpoints are account-catalog-specific.** Docs: "Use the generation endpoint available to
  your account" — therefore the model slug **must** be configurable, not hardcoded. Example endpoint
  patterns seen in docs: `higgsfield-ai/veo3.1`, `higgsfield-ai/sora-2/text-to-video`,
  `kling-video/v2.5-turbo/pro/text-to-video`.
- **Lifecycle:** `queued` → `in_progress` → terminal `completed` | `failed` | `nsfw` | `canceled`.
  The SDK surfaces typed statuses `Queued`, `InProgress`, `Completed`, `Failed`, `NSFW`, `Cancelled`.
- **Completed video output:** `result["video"]["url"]` (retained ≥ 7 days → copy to own storage).
- **Inputs:** image-to-video accepts a public HTTPS URL via the `image_url` argument (File uploads
  doc). Our scene visuals already come from public URLs (Pollinations), so no upload call is needed.
  If `image_url` is provided it is passed as-is; optional per model.

## Scope

1. `Settings`: add `higgsfield_api_key: str = ""` and `higgsfield_video_model: str = ""`.
2. `app/providers/video/higgsfield.py`:
   - `HiggsfieldVideoProvider(VideoProvider, ProviderInfoMixin)` implementing the existing
     `VideoProvider.generate(prompt, duration=5.0, image_url=None)` contract.
   - Capability metadata: `name="higgsfield"`, `vendor="higgsfield.ai"`, `capability=VIDEO`,
     `priority=5` (highest of the video providers), `models=["higgsfield_video_model"]`,
     `is_configured() = bool(settings.higgsfield_api_key)`.
   - **Lazy `import higgsfield_client`** inside `generate()` (never at module import, so tests and
     non-keyed installs don't require the package; on `ImportError` raise a RuntimeError with the
     `pip install higgsfield-client` hint).
   - Bridge our key into the SDK env (`os.environ["HF_KEY"] = settings.higgsfield_api_key`) before
     calling — our config uses `HIGGSFIELD_API_KEY`, the SDK reads `HF_KEY`.
   - `arguments = {"prompt": prompt}` (+ `image_url` when given). Model slug from
     `settings.higgsfield_video_model`; if empty, raise a clear error naming the setting.
   - Await `subscribe_async(model, arguments=arguments)`; map the SDK result to
     `VideoResult(url=result["video"]["url"], duration_seconds=duration)` with fallbacks for
     alternate output keys; raise `RuntimeError` on `failed`/`nsfw` including the SDK error/status.
2. **Router:** register `HiggsfieldVideoProvider` in `PROVIDER_REGISTRY[VIDEO]` ahead of Runway and
   Pollinations (priority 5). Resolution policy is unchanged: configured Higgsfield key → Higgsfield
   wins; else Runway if keyed; else Pollinations.
3. **Deps:** add `higgsfield-client` to `apps/api/requirements.txt`.
4. **Env/docs:** `.env.example` gains `HIGGSFIELD_API_KEY` + `HIGGSFIELD_VIDEO_MODEL`; README mention.

## Out of scope (deliberately deferred)

- **MCP server for tool use** (master spec mentions it): a standalone deliverable (an MCP server
  exposing platform tools) with its own lifecycle/auth needs — not part of adding a provider adapter.
  Tracked for a later phase.
- Wiring `video.generate` into the render pipeline (scene animation): that changes render output and
  is a product/UX decision (Phase 7 studio). The adapter is fully callable on demand.
- Webhooks (submit + receive completion): polling via SDK is sufficient; webhooks noted as recovery
  path for a future event-driven worker.

## Implementation Steps

1. `config.py`: add the two settings.
2. `providers/video/higgsfield.py`: provider class (lazy SDK import, HF_KEY bridge, subscribe_async,
   output parsing, error mapping).
3. `providers/router.py`: add to VIDEO registry.
4. `requirements.txt`, `.env.example`, `README.md`.
5. Tests (`tests/test_higgsfield.py`) + update `test_providers.py` inventory count (6 → 7).
6. Run backend gates; frontend untouched.
7. `docs/changes/0005` + audit row/banner.

## Acceptance Criteria

- With `higgsfield_api_key` set, `ProviderRouter().resolve(VIDEO)` returns `HiggsfieldVideoProvider`;
  with it unset, previous policy holds (Runway/Pollinations). `GET /api/providers` lists it as
  `configured: true/false` accordingly.
- `generate()` calls `subscribe_async` with the argument map above; returns `VideoResult` with the
  video URL from `result["video"]["url"]`.
- Image-to-video passes `image_url` through untouched.
- `failed`/`nsfw` results raise `RuntimeError` with the SDK-provided detail.
- Missing `higgsfield-client` raises a RuntimeError mentioning the pip install.
- Empty `higgsfield_video_model` raises a clear configuration error.
- All backend tests pass (existing 38 + new).

## Tests to Add

- `test_video_resolves_higgsfield_when_configured`
- `test_inventory_includes_higgsfield` (count 7, flags)
- `test_generate_submits_and_returns_video_url` (fake `higgsfield_client` module via
  `monkeypatch.setitem(sys.modules, ...)`, monkeypatched `subscribe_async`)
- `test_generate_passes_image_url`
- `test_generate_failed_status_raises`
- `test_generate_missing_sdk_raises_with_install_hint`
- `test_generate_missing_model_setting_raises`

## Risks / Notes

- Model-availability and exact output shapes differ per account/model. The adapter follows the
  documented `video.url` contract; output-key fallbacks and a configurable model slug keep it honest
  when the account's catalog differs. This is a genuine documented-availability caveat, not a silent
  substitution.
- Outputs expire after ~7 days on Higgsfield CDN; caller must copy to own storage (pipeline writes
  through `StorageBackend` when wired in Phase 7).
- SDK readiness: `higgsfield-client` requires the `HF_KEY` env var (bridged from our setting).