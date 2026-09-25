# Architecture Audit — AI Video Automation Platform

**Date:** 2026-09-25
**Scope:** Full repository review (backend, frontend, worker, packages, infrastructure, CI).
**Method:** Static analysis via imports, routes, references, runtime call sites, tests, configs, and documentation. No production data was touched.

> **Status update (2026-09-25, Phases 1–5 shipped).** A repair phase, a verified-cleanup phase, an
> async+persistence phase, a provider-boundaries phase, and a Higgsfield adapter phase have been
> delivered against this audit: the agent input-contract bug is fixed (`AgentInput | dict`
> normalization), the render pipeline persists Scripts/Scenes/GenerationJobs/Assets/RenderJobs, the
> render-status endpoint no longer crashes, 19→45 backend tests pass, all dead provider code / unused
> deps / empty scaffold dirs are removed, `create_all` is dropped in favor of Alembic (with migration
> `003`), renders can be dispatched to the Celery worker with real progress polling, providers live
> behind a formal boundary (capabilities, deterministic `ProviderRouter`, normalized `GenerationResult`,
> `GET /api/providers`), and a real AI-video provider (Higgsfield via the official `higgsfield-client`
> SDK) sits behind that boundary.
> `lint / type-check / test / build` all pass on both apps.
> See `docs/changes/0001…` through `docs/changes/0005-…`.
> Sections 4–7 below describe the state **as audited**; the follow-up section 11 (phased plan) tracks
> completion. Section 8 (Keep) and section 9 (Refactor/Add) remain the roadmap for phases 6+.

---

## 1. Executive Summary

The platform has a **solid skeleton and a broken runtime**. The declared architecture (5-agent pipeline, Celery worker, provider abstraction, monorepo packages, K8s/Terraform infrastructure) is largely **scaffolding or documentation fiction**. The code that actually ships today is:

- `apps/api` — FastAPI app with real models, routers, agents, and a working FFmpeg render pipeline.
- `apps/web` — Next.js 15 app with a **working but thin** generate-video flow and ~20 static placeholder screens.

The **primary user journey is broken**: the agent layer throws at runtime because every call site passes a plain `dict` to `BaseAgent.run()` (which requires an `AgentInput` dataclass). This crashes `/api/scripts/generate`, `/api/storyboard/generate`, `/api/trends/analyze`, `/api/agents/{name}/run`, and the entire `/api/render/start` pipeline (the core "create a video" feature). No test covers this path.

Around that core defect there is a large amount of verified dead code (celery tasks never dispatched, half the provider suite never instantiated, empty packages, empty schema layer, unused models/fields/settings/dependencies) and a frontend with 14/25 unused API methods and ~15 static mock screens.

**Verdict:** not a rewrite — a **surgical repair + cleanup + targeted feature work** against the existing structure. The existing FFmpeg renderer, storage abstraction, caption service, model schema, and agent separation are worth preserving.

---

## 2. Repository Map — Reality vs. README

| Path | README claims | Reality |
|---|---|---|
| `apps/web/` | Next.js 16 | **Next.js 15.1**, React 19, Tailwind v4. Real app. |
| `apps/api/` | FastAPI + SQLAlchemy async + Celery | **Real.** FastAPI + async SQLAlchemy + Celery (tasks dead). |
| `apps/worker/` | Celery beat scheduler | **Empty directory** (0 files, untracked). The only Celery worker lives in `apps/api`. |
| `packages/ai`, `config`, `types`, `ui` | Shared types/UI/utils | **All empty** (0 files, no package.json, never imported). |
| `infrastructure/docker/` | Dockerfiles | **Empty** (the only Dockerfile is `apps/api/Dockerfile`). |
| `infrastructure/kubernetes/` | K8s manifests | **Does not exist.** |
| `infrastructure/terraform/` | AWS/GCP provisioning | **Does not exist.** |
| `apps/web/Dockerfile` | (needed by docker-compose) | **Missing** — `docker compose up web` fails. |
| `docs/` | — | Did not exist (created by this audit). |
| `alembic.ini` | quick start runs migrations | **Gitignored** → missing on fresh clone; `alembic upgrade head` fails. |

Only **one Dockerfile** exists (`apps/api/Dockerfile`), and **only one markdown file** existed (`README.md`).

---

## 3. Current Architecture (Actual)

```
apps/web (Next.js 15.1, React 19)
   │  fetch() via src/lib/api.ts (Bearer JWT in localStorage)
   ▼
apps/api (FastAPI, SQLAlchemy async)
   ├─ /api/auth/*           register, login (JWT, bcrypt)
   ├─ /api/projects/*       CRUD
   ├─ /api/scripts/generate  → ScriptAgent (sync, BROKEN)
   ├─ /api/characters/*      → CharacterAgent (sync, BROKEN)
   ├─ /api/storyboard/generate → StoryboardAgent (sync, BROKEN)
   ├─ /api/trends/*          → TrendAgent (sync, BROKEN on analyze)
   ├─ /api/agents/*          → any agent by name (sync, BROKEN)
   ├─ /api/render/start      → VideoPipeline (sync long-blocking, BROKEN)
   ├─ /api/assets/*          upload/presign
   ├─ /api/analytics/*       DB reads (never written)
   └─ /api/prompts/*         DB CRUD (never seeded)
        │
        ├─ Agents  → app/agents/* (BaseAgent + 5 agents)
        ├─ Providers → app/providers/* (LLM OpenAI, Image Pollinations,
        │              Voice ElevenLabs, Video, Music, Transcription)
        ├─ Services → pipeline, render (FFmpeg), caption, storage (S3/Local)
        └─ Tasks   → app/tasks/* (Celery — defined, NEVER dispatched)

Celery worker (docker-compose) → idle; no beat schedule; nothing enqueues tasks.

DB: PostgreSQL 16 / Redis 7 / MinIO declared; storage defaults to local disk.
     In dev/tests: SQLite via aiosqlite (test.db).
```

The real flow that "works" today: **signup → create/new → createProject + startRender → content/projects**. The real flow that is *supposed* to work (script → storyboard → images → render) is **broken at the agent boundary**.

---

## 4. Backend Inventory

### 4.1 Routes (all registered in `app/main.py`)

| Endpoint | Status | Evidence |
|---|---|---|
| `GET /api/health` | ✅ works | used by tests |
| `POST /api/auth/register`, `/login` | ✅ works | tested |
| `GET/POST/PATCH/DELETE /api/projects*` | ✅ works | list/create/delete used by UI; get/patch unused |
| `POST /api/scripts/generate` | ❌ **broken** | passes dict to `agent.run()` → `AttributeError` (`base.py:37` → `script_agent.py:45` accesses `input.context`) |
| `POST /api/storyboard/generate` | ❌ **broken** | same dict/dataclass defect |
| `POST /api/trends/analyze` | ❌ **broken** | same defect |
| `POST /api/agents/{name}/run` | ❌ **broken** | same defect |
| `POST /api/characters*` | ❌ **broken** | same defect |
| `GET /api/characters*` | ⚠️ API-dead | never called by UI; UI uses hardcoded data |
| `POST /api/render/start` | ❌ **broken** | pipeline calls agents with dicts; also voice/video providers never invoked |
| `GET /api/render/status/{job_id}` | ❌ latent bug | `job.status.value` (`render.py:71`) on a `String` column; `RenderJob` rows never created |
| `POST/GET /api/assets/*` | ⚠️ API-dead | never called by UI; `Asset` rows never persisted |
| `GET /api/analytics*` | ⚠️ API-dead | never written → always empty; static UI |
| `GET/PATCH /api/prompts*` | ⚠️ API-dead | table never seeded; UI unused |
| `GET /api/agents/runs` | ⚠️ stub | hardcoded `{"runs": [], "total": 0}` |

### 4.2 Models / Tables (15 tables, migration `001_initial`)

Writable today: `users`, `projects`. Readable: `trends`, `video_analytics`, `prompt_templates` (all empty by default).

**Never written (no INSERT path anywhere):** `scripts`, `scenes`, `characters`, `assets`, `generation_jobs`, `render_jobs`, `publishing_jobs`, `ai_insights`, `api_keys`, `user_sessions`.

**Unused enums (columns are plain `String`):** `UserRole`, `ProjectStatus`, `ProjectType`.

**Schema note:** `main.py` lifespan runs `Base.metadata.create_all` on every startup — Alembic is effectively bypassed in dev/CI (tests use `create_all` too). Migration `001` matches models 1:1; no drift.

### 4.3 Agents

| Agent | Reachable? | Notes |
|---|---|---|
| `TrendAgent` | yes (broken) | `POST /api/trends/analyze`, also wrapped in dead celery task |
| `ScriptAgent` | yes (broken) | scripts route + pipeline |
| `CharacterAgent` | yes (broken) | characters route — UI never calls |
| `StoryboardAgent` | yes (broken) | storyboard route + pipeline |
| `QualityAgent` | **only** via dead celery task | no HTTP route ever invokes it |

All agents hardcode `model = "gpt-4o"`; all share `BaseAgent` (solid abstraction worth keeping).

**Critical cross-cutting defect:** `BaseAgent.run()` expects `AgentInput` dataclass; all 8+ call sites pass plain dicts (`scripts.py:40-47`, `characters.py:67-73`, `storyboard.py:33-39`, `trends.py:48`, `agents.py:50-53`, `pipeline.py:53-66`, `generation_tasks.py:28-64`). `build_messages()` then does `input.context.get(...)` on a `dict` → `AttributeError`. **Verified statically; uncaught because no test exercises an agent.**

### 4.4 Providers

| Provider module | Used? | Status |
|---|---|---|
| `providers/llm/openai.py` `OpenAIProvider` | ✅ | the only LLM provider used |
| `providers/llm/anthropic.py` `AnthropicProvider` | ❌ | never imported |
| `providers/llm/mock.py` `MockLLMProvider` | ❌ | never imported |
| `providers/image/providers.py` `PollinationsProvider` | ✅ | used in pipeline |
| `providers/image/providers.py` `MockImageProvider` | ❌ | dead |
| `providers/voice/providers.py` `ElevenLabsProvider`/`MockVoiceProvider` | ⚠️ | instantiated in pipeline (`pipeline.py:34`) but `synthesize()` **never called** |
| `providers/music/*` (3 providers) | ❌ | never imported; music never mixed |
| `providers/transcription/*` (2 providers) | ❌ | never imported |
| `providers/video/*` (3 providers) | ⚠️ | `get_video_provider()` called once, `.generate()` never called |
| `providers/base.py` ABCs | ✅ | the protocol layer — worth keeping, currently incomplete (no normalized `GenerationResult`, no Higgsfield) |

**Note:** `providers/base.py` already defines `LLMProvider`, `ImageProvider`, `VoiceProvider`, `VideoProvider`, `MusicProvider`, `TranscriptionProvider` ABCs with `LLMResponse`/`ImageResult`/`AudioResult`/`VideoResult` dataclasses. The abstraction the master spec calls for half-exists — it just isn't consistently used (agents take concrete `OpenAIProvider`; agents hardcode the model; results aren't normalized into one `GenerationResult`).

**Phase 4 update:** this boundary now exists — every provider declares a capability/priority/mock/`is_configured()` (via `ProviderInfoMixin`), `app/providers/router.py` provides deterministic policy-driven resolution plus `GET /api/providers`, and `GenerationResult`/`adapt()` normalize raw results. Providers previously flagged above as dead (`anthropic`, `mock`, music, transcription) were removed in Phase 2; `get_video_provider()` was superseded by the router in Phase 4.

### 4.5 Services

| Service | Status |
|---|---|
| `caption_service.py` | ✅ solid; `captions_to_srt` used; **`captions_to_ass`/`CaptionStyle`/`PRESETS` never called** |
| `render_service.py` | ✅ solid FFmpeg pipeline (slides → concat → audio → captions). Audio/music stages never feed input because pipeline never synthesizes voice/music |
| `storage_service.py` | ✅ good `StorageBackend` ABC + `LocalStorage`/`S3Storage` + factory |
| `pipeline.py` `VideoPipeline` | ⚠️ orchestration exists but is **synchronous, blocking, API-bound**, doesn't persist jobs, doesn't persist scenes/assets, and crashes on agent calls |

### 4.6 Tasks (Celery)

- `celery_app.py`: Redis broker, autodiscovery — fine.
- `generation_tasks.py`: `analyze_trend`, `generate_script`, `generate_storyboard`, `quality_check` — **defined but zero `.delay()`/`.apply_async` calls anywhere**. docker-compose `worker` service boots a worker with nothing to do. No beat schedule exists.

### 4.7 Config & Core

- `config.py` (pydantic-settings) — good. **Never-read settings:** `google_api_key`, `edge_tts_voice`, `pollinations_enabled`, `app_url`, `api_url`, `rate_limit_per_minute`, `max_monthly_cost_cents`, `default_quality`. No rate limiting/cost caps implemented despite settings.
- `core/security.py` — JWT + bcrypt, used correctly.
- `schemas/` — **empty package** (Pydantic schemas are inlined in routers — acceptable at this size, but inconsistent with the declared layout).

### 4.8 Tests (8 total, all passing)

- `tests/conftest.py`, `test_auth.py`, `test_health.py`, `test_projects.py`.
- **No coverage** for: scripts, characters, storyboard, agents, assets, render, trends, analytics, prompts, providers, pipeline, celery, or schema writes. This is why the critical defects survive.

---

## 5. Frontend Inventory

### 5.1 Structure

- 27 pages under `src/app/`: marketing `/`, auth (signin/signup), a dashboard shell `(dashboard)/` with sidebar and ~23 links, and route groups: `ai/*`, `analytics/*`, `content/*`, `create/*`, `discover/*`, `studio/*`, `settings`.
- `src/components/**` and `src/types/` — **completely empty** (0 files).
- No TanStack Query usage anywhere (`QueryClientProvider`, `useQuery`, `useMutation` all absent) despite `@tanstack/react-query` being a dependency. All data fetching is imperative `fetch` via `lib/api.ts`.
- Zustand `useAppStore` (`lib/store.ts`): 7 members, **5 never consumed** (`sidebarOpen`, `toggleSidebar`, `currentProject`, `setCurrentProject`, `generatingJob`, `setGeneratingJob`, `setToken`). Login writes `localStorage` directly, so the in-memory `token` in the store can go stale after SPA logout/login.
- No component library (empty Radix/CVA/framer-motion deps); all UI is inline Tailwind + `lucide-react`.

### 5.2 API usage

Methods **actually called** (11/25): `register, login, getProjects, createProject, deleteProject, generateScript, getAgents, runAgent, getTrends, analyzeTrend, startRender`.

**Unused (14/25):** `getProject, updateProject, getScript, getCharacters, createCharacter, updateCharacter, generateStoryboard, uploadAsset, getAgentRuns, getRenderStatus, getAnalytics, getVideoAnalytics, getPrompts, updatePrompt`.

### 5.3 Functional vs. static screens

| Screen | Status |
|---|---|
| `/auth/*`, `/content/projects`, `/create/new`, `/create/script`, `/discover/trends`, dashboard | **functional** (real API) |
| `/create/characters`, `/create/storyboard` | static mock + broken links (`/create/characters/new` → 404, `/create/characters/[id]` → 404) |
| `/discover/ideas`, `/discover/opportunities`, `/discover/instagram` | static mock |
| `/ai/agents` | functional (broken backend) |
| `/ai/costs`, `/ai/models`, `/ai/runs` | static mock |
| `/analytics/*` (3), `/content/calendar`, `/content/published`, `/settings` | static mock |
| `/studio/editor`, `/studio/assets`, `/studio/audio`, `/studio/captions` | static mock, no wiring |
| deep-links (`/create/new?topic=…`) | **broken** — `create/new` never reads `useSearchParams` |

### 5.4 Build/test/CI

- Vitest with a single test (`cn()`). **CI runs only lint + build for the frontend — never `npm run test`.**
- `npm run lint` uses `next lint` (deprecated in Next 15.1, removed in 16). ESLint stack version-skewed: root `eslint@10` / `eslint-config-next@16` vs web `eslint@9` / `eslint-config-next@15`.
- `next.config.mjs` rewrite `/api/* → localhost:8000` is **dormant** (client calls absolute `NEXT_PUBLIC_API_URL`).
- `next/image` unused; `framer-motion`, 10× `@radix-ui/*`, `date-fns`, `cva`, `tailwindcss-animate`, `@testing-library/react`, `@vitejs/plugin-react` (misplaced in `dependencies`) all unused.

---

## 6. Duplication & Obsolete

- **Env config duplicated** across `.env.example`, `docker-compose.yml`, and `ci.yml` (expected, but sync-sensitive).
- **`User` type** defined locally in frontend `store.ts` (`interface User`); backend model separate; no `packages/types` to share.
- **ESLint stack twice**, inconsistent versions.
- README describes 16 lines of endpoint/table/folder fiction.
- `httpx` listed twice in `requirements.txt`; `markdown`/`moviepy`/`edge-tts` referenced in comments but not used.

---

## 7. Verified Dead / Unused Inventory (with evidence)

### Backend
1. `providers/llm/anthropic.py` — never imported.
2. `providers/llm/mock.py` — never imported.
3. `providers/image/providers.py` `MockImageProvider` — never used.
4. `providers/music/__init__.py` (3 providers) — never imported.
5. `providers/transcription/__init__.py` (2 providers) — never imported.
6. `providers/video/__init__.py` `MockVideoProvider` — never used; `PollinationsVideoProvider`/`RunwayVideoProvider` `.generate()` never called.
7. `agents/quality_agent.py` — only via never-dispatched celery task.
8. `tasks/generation_tasks.py` — 4 tasks, zero dispatch; worker idle.
9. `schemas/` — empty package.
10. `api/agents.py get_agent_runs` — hardcoded stub.
11. Models never written: `Script`, `Scene`, `Character`, `Asset`, `GenerationJob`, `RenderJob`, `PublishingJob`, `AiInsight`, `ApiKey`, `UserSession`, `Trend`, `VideoAnalytics`, `PromptTemplate`.
12. Unused enums `UserRole`/`ProjectStatus`/`ProjectType`.
13. Unused settings: `google_api_key`, `edge_tts_voice`, `pollinations_enabled`, `app_url`, `api_url`, `rate_limit_per_minute`, `max_monthly_cost_cents`, `default_quality`.
14. Unused imports: `projects.py` (`Script`, `Scene`, `ProjectStatus`), `trends.py:10`/`analytics.py:10` (`AiInsight`).
15. `caption_service._format_ass_time`/ASS path, `CaptionStyle`, `PRESETS` — never called.
16. `test.db`, `.pytest_cache` — local artifacts.
17. `apps/worker/`, `infrastructure/docker/` (empty), `infrastructure/kubernetes/`, `infrastructure/terraform/` — nonexistent/empty.
18. `apps/web/Dockerfile` — missing.

### Frontend
19. Empty trees `src/components/**`, `src/types/`.
20. Unused deps (no imports): all Radix, `@tanstack/react-query`, `framer-motion`, `date-fns`, `cva`, `tailwindcss-animate`, `@testing-library/react`, `@vitejs/plugin-react` (runtime).
21. Unused API methods (14/25) listed above.
22. Unused store members (5/7).
23. Unused utils `formatDuration`/`formatCost`/`formatDate`.
24. Dormant rewrite in `next.config.mjs`.

### Root/Infra
25. `packages/*` (4 empty dirs), empty workspace claim.
26. `alembic.ini` gitignored.
27. `deploy.yml` references Railway/Vercel with no platform config files (not necessarily bad; just fictional until used).

---

## 8. Worth Preserving (Keep)

- **`BaseAgent` abstraction** (`agents/base.py`) — clean `run()`/`build_messages()`/`parse_response()` contract + metadata tracking.
- **Provider ABC layer** (`providers/base.py`) — replaceability half-built; extend, don't replace.
- **`render_service.py`** — genuinely functional FFmpeg renderer with config, progress callbacks, caption burn-in.
- **`caption_service.py`** word-level captioning + SRT.
- **`storage_service.py`** storage ABC + Local/S3.
- **Core security** (JWT/bcrypt/HTTPBearer) and auth/projects routers.
- **DB model design** (15 tables is reasonable for the domain; the problem is no writes, not the schema).
- **Pollinations + OpenAI providers; FFmpeg path; Celery+Redis if we actually dispatch**.
- Frontend: the dashboard shell, `lib/api.ts` client (slim it), `/create/new` wizard concept, `/content/projects`.

---

## 9. Recommendations (Keep / Refactor / Remove / Add)

### Remove (evidence above, low risk)
- Dead providers: Anthropic LLM, Mock LLM/Image/Video/Voice, Music (all 3), Transcription (all 2), unused video providers.
- Empty dirs `apps/worker`, `packages/ai|config|types|ui`, `infrastructure/docker` (until used), `src/components/**`, `src/types/`.
- Unused frontend deps + store members + utils + rewrite config.
- Unused settings, enums, imports, stub endpoint.
- Local artifacts (`test.db`, `.pytest_cache`).

### Refactor / Fix (high value)
- **Fix agent input contract** (dict → `AgentInput`, or accept both) — unlocks the whole product.
- **Remove automatic `create_all`**; standardize on Alembic; add `alembic.ini` to git.
- **Persist writes**: script/scene/asset/job persistence in current flows, and actually invoke voice/video providers (or remove them until used).
- **Move rendering off the request thread** — dispatch to Celery (existing!) and add real status polling; the "create/new" progress bar is cosmetic today.
- **Slim the API client / store / utils** to what's used; add TanStack Query properly or drop it.
- **Wire `useSearchParams` topic hand-off** from discover → create.
- **Version/alembic consistency, `next lint` replacement, CI frontend test job.**

### Add (SDD, phased, only where valuable)
- Higgsfield as a first-class `VideoGenerationProvider` behind the existing `providers/base.py` boundary (normalized `GenerationResult`, server-side credentials only).
- Provider router (deterministic, policy-driven), cost tracking, structured QA, scene regeneration, persistent workflow state — per Phase 5–6 of the plan below.
- `docs/specs/` + `docs/changes/` for all meaningful changes.

---

## 10. Top Risks / Blockers

1. **Agent layer defect** breaks the primary product path — highest priority, smallest fix.
2. **Synchronous long-running renders** in the API request lifecycle — reliability + UX blocker once generation works.
3. **No worker dispatch** despite Celery+Redis infra — the async backbone is unused.
4. **No provider/agent/pipeline tests** — regressions invisible.
5. **Frontend breadth far exceeds working backend** — 20 static screens create maintenance drag and misleading UX; prioritize the core journey instead of filling shells.

---

## 11. Proposed Phased Plan (SDD-driven)

| Phase | Scope | Primary deliverable | Status |
|---|---|---|---|
| **0** | Audit | `docs/architecture/ARCHITECTURE_AUDIT.md` | ✅ done |
| **1** | Fix broken core | Agent input contract fix, script persist, render status fix → **"create a video" works end-to-end synchronously** | ✅ done (`docs/changes/0001-…`) |
| **2** | Verified cleanup | Remove dead code/deps/settings/dirs; run lint+tests+build | ✅ done (`docs/changes/0002-…`) |
| **3** | Async + persistence | Dispatch pipeline via existing Celery+Redis; real progress/status; job/scene/asset persistence; migrations standard (drop `create_all`) | ✅ done (`docs/changes/0003-…`) |
| **4** | Boundaries | Normalize `GenerationResult`, formalize provider capability protocols, provider router | ✅ done (`docs/changes/0004-…`) |
| **5** | Higgsfield | Adapter behind provider boundary per current official docs; MCP for tool use | ✅ done — adapter shipped (`docs/changes/0005-…`); MCP server deferred to a standalone phase |
| **6** | Quality + cost + scenes | Structured QA, cost tracking, scene regeneration, generation lineage | ⛔ not implemented — run finalized at Phase 5 |
| **7** | Product UX | Real studio view (scenes editable/regeneratable), progress clarity, remove/retire dead screens | ⛔ not implemented — run finalized at Phase 5 |
| **8** | Hardening | Security, tests around failure modes, lint/typecheck/build/tests in CI, README truth | ⛔ not implemented — run finalized at Phase 5 |

Each phase gets a small spec in `docs/specs/` + a change log entry in `docs/changes/` before implementation, and passes lint/tests/build before completion.

> **Run finalization (2026-09-25):** the phased SDD run concluded at **Phase 5**. Phases 6–8 are
> intentionally **not implemented** (work was scoped by the user to the five shipped phases).
> Recommended entry points for any future continuation, in priority order:
> Phase 6 lineage/cost (persist `metadata["providers"]` + `GenerationResult` already produced by the
> pipeline), Phase 8 CI/test hardening, then Phase 7 product UX.