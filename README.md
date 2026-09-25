# AI Video Automation Platform

Production-grade AI-powered video generation platform with a 5-agent architecture:
**give it an idea → script → storyboard → scene visuals → captions → render → review.**

## Architecture

```
apps/
  web/    Next.js 15, React 19, TypeScript, Tailwind CSS v4, Zustand
  api/    FastAPI, SQLAlchemy 2.0 (async), Celery, FFmpeg
infrastructure/
  database/init.sql
docs/
  architecture/   Architecture audit + roadmap
  specs/          Spec-driven development (SDD) specs
  changes/        Change log entries per spec
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS v4, Zustand |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Celery |
| Database | PostgreSQL 16, SQLite (dev/test) |
| Storage | MinIO (S3-compatible), Local filesystem |
| AI | OpenAI (LLM), Pollinations (images), ElevenLabs (voice, optional) |
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

# Frontend
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

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

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register user |
| POST | /api/auth/login | Login |
| GET/POST | /api/projects | List / create projects |
| GET/PATCH/DELETE | /api/projects/{id} | Get / update / delete project |
| POST | /api/scripts/generate | Generate a script with AI (optionally persists to a project) |
| GET | /api/scripts/{id} | Get a persisted script |
| GET/POST | /api/characters | List / create characters |
| PATCH | /api/characters/{id} | Update a character |
| POST | /api/storyboard/generate | Generate a storyboard with AI |
| POST | /api/render/start | Render a video (persists RenderJob, Script, Scenes, Assets) |
| GET | /api/render/status/{job_id} | Poll a render job |
| POST/GET | /api/assets | Upload / list assets |
| GET | /api/trends | Get trending topics |
| POST | /api/trends/analyze | Analyze a topic with TrendAgent |
| GET | /api/agents | List agents |
| POST | /api/agents/{name}/run | Run an agent by name |
| GET | /api/analytics* | Analytics (reads) |
| GET/PATCH | /api/prompts* | Prompt template library |

Full route list: `app/main.py`.

## Database

15 tables across 10+ models:

- **users**, **user_sessions** - Auth
- **projects** - Video projects with status tracking
- **scripts** - Generated scripts with structure
- **scenes** - Scene-by-scene breakdowns
- **characters** - Persistent character personas
- **assets** - Generated media files
- **generation_jobs** - AI generation task tracking (model/tokens/cost/attempts)
- **render_jobs** - Video render progress
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
JWT_SECRET=your-secret-key
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...        # optional; falls back to MockVoiceProvider
RUNWAY_API_KEY=...            # optional; video provider fallback to Pollinations
HIGGSFIELD_API_KEY=...        # optional; preferred video provider (official higgsfield-client SDK)
HIGGSFIELD_VIDEO_MODEL=...    # e.g. higgsfield-ai/veo3.1 — use a slug available to your account
```

## Testing

```bash
# Backend
cd apps/api
pytest -v

# Frontend
cd apps/web
npm run test:run
npm run lint
npm run type-check
npm run build
```

## Documentation

- `docs/architecture/ARCHITECTURE_AUDIT.md` — repository audit and phased roadmap
- `docs/specs/*` — approved specs (SDD)
- `docs/changes/*` — per-spec change logs