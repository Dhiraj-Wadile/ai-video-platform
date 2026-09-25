# Change 0002 — Verified cleanup

Date: 2026-09-25 · Phase 2 · Spec: `docs/specs/0002-verified-cleanup.md`

## What changed

### Backend (`apps/api`)
- **Deleted** `providers/llm/anthropic.py`, `providers/llm/mock.py` (Anthropic/Mock LLM providers — zero imports).
- **Deleted** `providers/music/` (Pixabay/FreeSound/Mock) and `providers/transcription/` (Whisper/Mock) — modules never imported.
- **`providers/image/providers.py`** — removed `MockImageProvider`.
- **`providers/video/__init__.py`** — removed `MockVideoProvider`; kept `PollinationsVideoProvider` (live fallback) and `RunwayVideoProvider`.
- **`config.py`** — removed never-read settings: `google_api_key`, `edge_tts_voice`, `pollinations_enabled`, `app_url`, `api_url`, `rate_limit_per_minute`, `max_monthly_cost_cents`, `default_quality`.
- **`requirements.txt`** — dropped `anthropic`, deduped `httpx`, kept everything actually imported.
- **`.env.example`** — removed matching unused keys.
- **`alembic.ini`** — now tracked (was gitignored → fresh clones couldn't migrate). Minimal config pointing at `migrations/`.

Kept deliberately (documented in spec): `QualityAgent`, Celery tasks (dispatched in a later phase), `MockVoiceProvider` (live fallback), caption ASS styling (planned studio feature), all DB tables/models.

### Frontend (`apps/web`)
- **package.json** — removed unused deps (10× `@radix-ui/react-*`, `@tanstack/react-query`, `framer-motion`, `date-fns`, `class-variance-authority`, `tailwindcss-animate`, `@testing-library/react`, `autoprefixer`, `@vitejs/plugin-react`). Aligned ESLint stack to `eslint@^9` + `eslint-config-next@^15` (matches Next 15.1; the previous `eslint@10`/`eslint-config-next@16` stack crashed on `eslint-plugin-react` and `scopeManager.addGlobals`).
- **Root package.json** — removed unused root ESLint deps (no root eslint config; turbo runs per-workspace lint).
- **eslint.config.mjs** — rewritten to use `FlatCompat` over `next/core-web-vitals` (the officially supported flat-config bridge for Next 15 + ESLint 9; v15 ships no native flat export).
- **vitest.config.ts** — removed `@vitejs/plugin-react`; fixed `@` alias to an absolute path (relative alias failed to resolve in vitest).
- **lint script** — `next lint` → `eslint .`.

### Repo structure
- Removed empty scaffold dirs (untracked): `apps/worker/`, `packages/ai|config|types|ui`, `infrastructure/docker/`, `apps/web/src/components/`, `apps/web/src/types/`.
- **`apps/web/Dockerfile`** — added minimal dev image so the `web` service in `docker-compose.yml` is no longer broken.

### Docs
- **`README.md`** — rewritten to match reality (Next.js 15, actual folder layout, actual endpoints, honest quick-start; removed 16 lines of fiction; documented `docs/`).

## Verification
- Backend: `pytest -v` → **19 passed**.
- Backend: `python -c "import app.main"` → OK; `py_compile` on all touched files → OK.
- Frontend: `eslint .` → 0 errors (3 pre-existing a11y warnings), `tsc --noEmit` → pass, `vitest run` → 1 passed, `next build` → success.
- Grep: no references to removed symbols anywhere outside `docs/` (which records their removal).

## Compatibility
- Zero behavior change to routes, models, or the pipeline. Removed code had no import/reference sites.