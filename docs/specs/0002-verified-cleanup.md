# Spec 0002 — Verified cleanup (Phase 2)

Status: Approved (Phase 2)
Date: 2026-09-25

## Problem

The repo carries substantial verified dead code (providers never used, empty scaffold directories,
unused dependencies and settings) and the frontend verification gates are broken: `next lint`
(fire) is removed in Next 15 and crashes under the eslint 10 config, and vitest cannot load
`@vitejs/plugin-react@8` (ESM-only) from a CJS config. Phase 2 of the plan must remove dead
weight and make `lint / typecheck / test / build` actually pass.

## Goal

Smaller, truthful repo with the same capability, and all four verification gates green:
`pytest`, `vitest`, `tsc --noEmit`, `eslint .`, `next build`.

## Non-goals

No behavior change to routes/models/pipeline. No provider, agent, or schema additions. Node-phase
removals are strictly code that has zero references.

## Removals (each verified by grep/import scan in the audit)

Backend (`apps/api`):
1. `providers/llm/anthropic.py` (AnthropicProvider) — zero imports.
2. `providers/llm/mock.py` (MockLLMProvider) — zero imports.
3. `providers/image/providers.py::MockImageProvider` — zero references.
4. `providers/video/__init__.py::MockVideoProvider` — zero references.
5. `providers/music/` (Pixabay/FreeSound/Mock) — module never imported.
6. `providers/transcription/` (Whisper/Mock) — module never imported.
7. Settings never read: `google_api_key`, `edge_tts_voice`, `pollinations_enabled`, `app_url`,
   `api_url`, `rate_limit_per_minute`, `max_monthly_cost_cents`, `default_quality`.
8. Unused imports: `pipeline.py` (`asyncio`, `uuid`, `time`); `trends.py`/`analytics.py` (`AiInsight`).
9. `requirements.txt`: drop `anthropic>=0.18.0` (unused provider), dedupe `httpx`.

Kept (deliberately, documented): `QualityAgent`, Celery tasks (`Phase 3` dispatches them),
`providers/voice` (MockVoiceProvider is the live fallback in `pipeline.py`), caption styling
(`captions_to_ass` / `CaptionStyle` / `PRESETS` — used by the planned captions studio feature),
all DB tables/models (defined product features; deletes would require migration + later re-add).

Frontend (`apps/web`):
10. Unused deps (zero imports in `src/`): 10× `@radix-ui/react-*`, `@tanstack/react-query`,
    `framer-motion`, `date-fns`, `class-variance-authority`, `tailwindcss-animate`,
    `@testing-library/react`, `autoprefixer`. Remove `@vitejs/plugin-react` (no longer needed once
    vitest config no longer uses it).
11. Fix `lint` script: `next lint` → `eslint .`.
12. Rewrite `eslint.config.mjs` to consume `eslint-config-next/core-web-vitals` (flat config, v16
    native) instead of the obsolete `FlatCompat` bridge.
13. `vitest.config.ts`: drop the `@vitejs/plugin-react` plugin (no component tests exist; plain TS
    + jsdom is enough).

Repo structure:
14. Remove empty scaffold dirs (untracked, but misleading): `apps/worker/`, `packages/ai|config|types|ui`,
    `infrastructure/docker/`, `apps/web/src/components/*`, `apps/web/src/types/`.

Docs/config truth:
15. `apps/api/app/config.py` — remove unused settings (see #7).
16. `.env.example` — remove matching keys.
17. `README.md` — correct stack (Next.js 15), endpoints table, folder reality; note `docs/`.

## Architecture impact

None. Pure deletion + config/tooling correction.

## Risks

- Removing a dep that a future phase re-installs — accepted; the removal rule is evidence-based and
  re-installation is trivial.
- ESLint config rewrite may surface new (pre-existing) lint errors — fix only if trivial.

## Acceptance criteria

- [ ] Backend `pytest -v` → all pass (19 existing + any new).
- [ ] `apps/api` imports cleanly.
- [ ] Web: `npm run eslint`/`eslint .` exit 0; `npm run type-check` exit 0; `npm run test:run` exit 0.
- [ ] Web `npm run build` succeeds.
- [ ] Root `npm run lint` (turbo) succeeds.
- [ ] No references to removed symbols anywhere (grep).

## Implementation steps

1. Backend: delete files/classes/settings/imports; update `requirements.txt`.
2. Frontend: package.json cleanup; eslint config + lint script; vitest config.
3. Delete empty scaffold dirs.
4. Update `.env.example` and `README.md`.
5. Run all verification gates; document in `docs/changes/0002-verified-cleanup.md`.
6. Update `ARCHITECTURE_AUDIT.md` (mark Phase 2 done).