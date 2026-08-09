# AI Video Automation Platform

Production-grade AI-powered video generation platform with a 5-agent architecture.

## Architecture

```
apps/
  web/          Next.js 16, React 19, TypeScript, Tailwind CSS
  api/          FastAPI, SQLAlchemy (async), Celery
  worker/       Celery beat scheduler
packages/
  shared/       Shared types and utilities
  ui/           Shared UI components
infrastructure/
  docker/       Dockerfiles
  kubernetes/   K8s manifests
  terraform/    AWS/GCP provisioning
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, Zustand, TanStack Query, Framer Motion |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Celery |
| Database | PostgreSQL 16, Redis 7 |
| Storage | MinIO (S3-compatible), Local filesystem |
| AI | OpenAI, Anthropic, Pollinations, ElevenLabs |
| Video | FFmpeg (scene assembly, captions, transitions) |

## AI Agents

| Agent | Purpose |
|-------|---------|
| TrendAgent | Discovers trending topics from multiple sources |
| ScriptAgent | Generates scripts with hook/setup/conflict/payoff/CTA structure |
| CharacterAgent | Maintains consistent character personas |
| StoryboardAgent | Creates scene-by-scene breakdowns with visual directions |
| QualityAgent | Reviews output for engagement, accuracy, brand safety |
| AnalyticsAgent | Analyzes performance and generates optimization insights |

## Quick Start

```bash
# Start infrastructure
docker-compose up -d postgres redis minio

# Backend
cd apps/api
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register user |
| POST | /api/auth/login | Login |
| GET | /api/projects | List projects |
| POST | /api/projects | Create project |
| GET | /api/projects/{id} | Get project |
| POST | /api/scripts/generate | Generate script with AI |
| GET | /api/characters | List characters |
| POST | /api/characters | Create character |
| POST | /api/storyboard/generate | Generate storyboard |
| POST | /api/render/{project_id} | Render video |
| GET | /api/trends | Get trending topics |
| GET | /api/analytics/overview | Analytics overview |
| POST | /api/agents/run | Run AI agent |

## Database

15 tables across 10 models:

- **users** - User accounts
- **projects** - Video projects with status tracking
- **scripts** - Generated scripts with structure
- **scenes** - Scene-by-scene breakdowns
- **characters** - Persistent character personas
- **assets** - Generated media files
- **generation_jobs** - AI generation task tracking
- **render_jobs** - Video render progress
- **publishing_jobs** - Platform publishing status
- **trends** - Trending topic data
- **video_analytics** - Performance metrics
- **ai_insights** - AI-generated recommendations
- **prompt_templates** - Reusable prompt library
- **api_keys** - Encrypted API key storage
- **user_sessions** - JWT session tracking

## Environment Variables

Copy `.env.example` to `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_video_platform
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
```

## Testing

```bash
# Backend
cd apps/api
pytest -v

# Frontend
cd apps/web
npm run test
```
