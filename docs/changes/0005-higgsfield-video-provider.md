# Change 0005: Higgsfield Video Provider

**Date:** 2026-09-25
**Phase:** 5 (Higgsfield)
**Spec:** [0005-higgsfield-video-provider.md](../specs/0005-higgsfield-video-provider.md)
**Status:** Shipped

## Summary

Added a real, official AI-video provider behind the Phase 4 boundaries: `HiggsfieldVideoProvider`
implements the existing `VideoProvider.generate()` contract using the official `higgsfield-client`
Python SDK (`subscribe_async`), and the router now prefers Higgsfield for the video capability
whenever a `HIGGSFIELD_API_KEY` is configured.

## Facts confirmed against official docs (2026-09-25)

- Official Python SDK: `pip install higgsfield-client`; async `subscribe_async(model, arguments=...)`
  submits, polls, and waits (typed statuses `Queued`/`InProgress`/`Completed`/`Failed`/`NSFW`/`Cancelled`).
- Credentials via env `HF_KEY="key-id:key-secret"` (or `HF_API_KEY` + `HF_API_SECRET`).
- Model endpoints are **account-catalog-specific** (must be configurable, never hardcoded).
- Completed video output: `result["video"]["url"]`; outputs retained ≥ 7 days (copy to own storage).
- Image inputs accept a public HTTPS URL via `image_url` — no upload call needed for scene visuals.

## Changes

### Backend

- `app/config.py`: `higgsfield_api_key: str = ""`, `higgsfield_video_model: str = ""`.
- `app/providers/video/higgsfield.py` (new): `HiggsfieldVideoProvider(VideoProvider, ProviderInfoMixin)`
  — `name="higgsfield"`, `vendor="higgsfield.ai"`, `capability=VIDEO`, `priority=5`,
  `is_configured()` checks the API key.
  - `generate(prompt, duration, image_url=None)`:
    - lazy `import higgsfield_client` (ImportError → RuntimeError with `pip install higgsfield-client` hint);
    - bridges `HIGGSFIELD_API_KEY` → SDK env `HF_KEY`;
    - requires `HIGGSFIELD_VIDEO_MODEL` (clear error naming the setting);
    - `arguments = {"prompt": prompt}` (+ `image_url` passthrough);
    - awaits `subscribe_async(model, arguments=...)`, raises `RuntimeError` on
      `failed`/`nsfw`/`canceled`, maps `result["video"]["url"]` → `VideoResult` (with `videos[0]`
      fallback and a "no video URL" guard).
- `app/providers/router.py`: VIDEO registry = `[Higgsfield, Runway, Pollinations]`.
- `apps/api/requirements.txt`: added `higgsfield-client>=1.0.0`.
- `.env.example` / `README.md`: `HIGGSFIELD_API_KEY`, `HIGGSFIELD_VIDEO_MODEL` documented.

### Deferred (documented in spec)

- **MCP server for tool use** — standalone deliverable, not part of a provider adapter; tracked for a
  later phase. Pipeline wiring of `video.generate` into renders is Phase 7 (studio) scope; webhook
  mode is a future event-driven worker enhancement.

## Verification

- Backend: `python -m pytest -q` → **45 passed** (new `tests/test_higgsfield.py`: resolve-to-Higgsfield
  when keyed, inventory entry/count 7 + flags, submit→`VideoResult` mapping + argument capture,
  `image_url` passthrough, `nsfw`/`failed` → RuntimeError, missing-SDK install hint, missing-model
  config error). `test_providers.py` inventory count updated to 7.
- No `higgsfield_client` import at startup (lazy), so un-keyed installs/dev/test remain import-clean
  (verified via `python -c "import app.main"` + inventory smoke test).
- Frontend untouched this phase.

## Notes / Follow-ups

- Model/output shapes can vary by account; the spec flags this as a documented-availability caveat
  (configurable slug + output-key fallbacks) rather than a silent substitution.
- When the render pipeline animates scene visuals (Phase 7), completed Higgsfield URLs must be copied
  through `StorageBackend` before the 7-day retention expires.
- `GET /api/providers` now reports `video:higgsfield` with its configured flag.