# AI Video Automation Platform

Production-grade AI-powered video generation platform with a 5-agent architecture:
**give it an idea → script → storyboard → scene visuals → captions → render → review.**

## Architecture

```
apps/
  web/    Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS v4, Zustand
  api/    FastAPI, SQLAlchemy 2.0 (async), Celery, FFmpeg
infrastructure/
  database/init.sql
docs/
  architecture/   Architecture audit + roadmap
  specs/          Spec-driven development (SDD) specs
  changes/        Change log entries per spec
```

`apps/web` and the root share one npm workspace: install from the repository root.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS v4, Zustand |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Celery |
| Database | PostgreSQL 16, SQLite (dev/test) |
| Storage | MinIO (S3-compatible), Local filesystem |
| AI | OpenAI (LLM + TTS), Higgsfield (video, primary), Pollinations (images/video fallback), ElevenLabs (voice, optional) |
| Video | FFmpeg (scene assembly, captions, transitions) |

## AI Agents

| Agent | Purpose |
|-------|---------|
| TrendAgent | Discovers trending topics |
| ScriptAgent | Generates scripts with hook/setup/conflict/payoff/CTA structure |
| CharacterAgent | Maintains consistent character personas |
| StoryboardAgent | Creates scene-by-scene breakdowns with visual directions |
| QualityAgent | Reviews output for engagement, accuracy, brand safety |

All agents share the `BaseAgent` contract (input normalization, structured JSON output, usage metadata).
Every run is persisted to `generation_jobs`, which is what the Runs and Costs screens read.

## The Product Journey

| Screen | What it does |
|--------|--------------|
| `/dashboard` | Your projects, recent renders and spend at a glance |
| `/create/new` | Topic or script → generate; live progress, then lands in the scene studio |
| `/create/script` | Write or generate a script (hook → setup → conflict → payoff → CTA) |
| `/create/characters` | Persistent character personas reused across scenes |
| `/create/storyboard` | Scene-by-scene plan with visual directions |
| `/studio/editor` | **Scene studio:** watch the render, edit any scene inline, regenerate one visual or re-render the project |
| `/content/projects` | Every project, with quality verdict, cost and direct access to the studio |
| `/analytics/overview` | Views, engagement and top videos for your projects |
| `/ai/agents` `/ai/runs` `/ai/costs` | Agent library, run history with tokens/latency/errors, spend by project |
| `/settings` | Account plus live provider status (keys stay server-side) |
| `/discover/trends` | Trending topics from TrendAgent |

## Quick Start

```bash
# Start infrastructure (PostgreSQL, Redis, MinIO)
docker-compose up -d postgres redis minio

# Backend
cd apps/api
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend (npm workspaces — install once from the repo root)
npm install                    # in the repository root
cd apps/web
npm run dev                    # or: npm run dev from the root (turbo)
```

Open http://localhost:3000 and sign in. Provider keys are optional: without them the app runs on
mock/fallback providers so the whole journey is still usable, and `/settings` shows what is
configured.

### Async renders (optional)

By default renders run synchronously inside the API request. To dispatch renders to the Celery
worker and poll real progress instead, set `RENDER_ASYNC=true` and start a worker:

```bash
docker-compose up -d redis
celery -A app.tasks.celery_app worker --loglevel=info   # or: docker-compose up worker
```

`POST /api/render/start` then returns `{"status": "queued", "job_id", ...}` immediately and the
worker updates the `RenderJob` (progress/message/status). Poll with `GET /api/render/status/{job_id}`.

## API Endpoints

Every route below requires a bearer token except register/login. Rows addressed by id are
ownership-checked: another user's project, script, job or asset returns `404`, not `403`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register user |
| POST | /api/auth/login | Login |
| GET/POST | /api/projects | List / create projects |
| GET/PATCH/DELETE | /api/projects/{id} | Get / update / delete project |
| GET | /api/projects/{id}/detail | Project with scenes, assets and render jobs |
| PATCH | /api/projects/{id}/scenes/{scene_id} | Edit scene fields (narration, visual, caption, camera, duration…) |
| POST | /api/projects/{id}/scenes/{scene_id}/regenerate | Regenerate one scene's visual |
| GET | /api/projects/{id}/quality | Quality review result |
| POST | /api/projects/{id}/quality/review | Run QualityAgent over a render |
| GET | /api/projects/{id}/costs | Token + cost totals for one project |
| GET | /api/projects/{id}/lineage | Which agent produced which asset |
| POST | /api/scripts/generate | Generate a script with AI (optionally persists to a project) |
| GET | /api/scripts/{id} | Get a persisted script |
| GET/POST | /api/characters | List / create characters |
| GET/PATCH | /api/characters/{id} | Get / update a character |
| POST | /api/storyboard/generate | Generate a storyboard with AI |
| POST | /api/render/start | Render a video (persists RenderJob, Script, Scenes, Assets) |
| GET | /api/render/status/{job_id} | Poll a render job |
| POST | /api/render/recut | Re-cut an existing render with new pacing |
| POST | /api/assets/upload | Upload media under a project you own (`project_id` required) |
| GET | /api/assets/{key} | Resolve a storage URL for an asset you own |
| GET | /api/trends | Get trending topics |
| POST | /api/trends/analyze | Analyze a topic with TrendAgent |
| GET | /api/agents | List agents |
| GET | /api/agents/runs | Recent agent runs (tokens, latency, cost, errors) |
| POST | /api/agents/{agent_name}/run | Run an agent by name |
| GET | /api/analytics | Aggregates across your projects |
| GET | /api/analytics/{project_id} | Per-video metrics for one project |
| GET | /api/costs | Spend by project, cost per call, latency |
| GET/PATCH | /api/prompts, /api/prompts/{id} | Prompt template library |
| GET | /api/providers | Which providers are configured (names + readiness only) |
| GET | /api/health | Liveness |

Full route list: `app/main.py`.

## Database

17 tables across 12 models:

- **users**, **user_sessions** - Auth
- **projects** - Video projects with status tracking
- **scripts** - Generated scripts with structure
- **scenes** - Scene-by-scene breakdowns
- **characters** - Persistent character personas
- **assets** - Generated media files
- **generation_jobs**, **generation_records** - AI task tracking (model/tokens/cost/attempts) and raw outputs
- **render_jobs** - Video render progress
- **quality_reviews** - QualityAgent verdicts
- **publishing_jobs** - Platform publishing status
- **trends**, **video_analytics**, **ai_insights** - Discovery + analytics
- **prompt_templates** - Reusable prompt library
- **api_keys** - Encrypted API key storage

Schema migrations live in `apps/api/migrations/versions/` (Alembic). Run `alembic upgrade head` before
starting the API — the app does **not** create tables at startup.

## Environment Variables

Copy `.env.example` to `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_video_platform
REDIS_URL=redis://localhost:6379
JWT_SECRET=change-me                     # required in any real deployment
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...        # optional; falls back to MockVoiceProvider
RUNWAY_API_KEY=...            # optional; video provider fallback to Pollinations
HIGGSFIELD_API_KEY=...        # optional; preferred video provider (official higgsfield-client SDK)
HIGGSFIELD_VIDEO_MODEL=...    # e.g. higgsfield-ai/veo3.1 — use a slug available to your account
STORAGE_BACKEND=local         # local | s3 (minio)
RENDER_ASYNC=false            # true dispatches renders to the Celery worker
```

`JWT_SECRET` has a development default so a fresh clone runs, and the API logs a warning on every
startup while that default is in use. Set it before exposing the app: tokens signed with the default
are forgeable by anyone who has read the repository.

## Testing

```bash
# Backend (SQLite by default; set DATABASE_URL to run against PostgreSQL)
cd apps/api
pytest -v

# Frontend
cd apps/web
npm run lint
npm run type-check
npm run test:run     # one-shot; `npm test` is watch mode
npm run build
```

CI (`.github/workflows/ci.yml`) runs the backend suite on SQLite **and** PostgreSQL, and the frontend
lint / type-check / unit tests / build.

## Documentation

- `docs/architecture/ARCHITECTURE_AUDIT.md` — repository audit and phased roadmap
- `docs/specs/*` — approved specs (SDD)
- `docs/changes/*` — per-spec change logs