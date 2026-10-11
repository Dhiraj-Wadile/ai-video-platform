# Credentials Guide

Where to get every key, what it unlocks, and the order to collect them. Copy
`.env.example` to `.env` and fill values in as you go — the app boots with **zero
keys** in a limited demo mode, so you can start immediately and add keys later.

## What works with no keys

| Feature | No-key behaviour |
| --- | --- |
| Scene images | Pollinations.ai (free) |
| Video clips | Pollinations.ai (free) fallback |
| Narration voice | Silent mock voice |
| Scripts / storyboard / trends / quality | **Do not work** — the LLM needs a key |
| Publishing | Simulated "mock" publisher (records jobs, no real post) |
| Billing | Demo upgrade mode (no charge, plan changes immediately) |

---

## Recommended order

1. `JWT_SECRET` (core) — required before exposing the app to anyone.
2. `OPENAI_API_KEY` — the single most important key; unlocks the whole pipeline.
3. `ELEVENLABS_API_KEY` — real narration instead of silence.
4. `HIGGSFIELD_API_KEY` or `RUNWAY_API_KEY` — real video clips (optional; Pollinations is free).
5. Database + Redis — for production (not needed for local dev).
6. Social publishing tokens — one per platform you want to post to.
7. Stripe keys — to actually charge for plans.

---

## Core

### `JWT_SECRET`
Signs login tokens. Anyone who knows it can forge logins.
Generate: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
Set a long random value in production. `JWT_ALGORITHM` / `JWT_EXPIRATION_MINUTES`
can stay at defaults.

### `DATABASE_URL`
Dev default is SQLite (`sqlite+aiosqlite:///./app.db`). For production use a hosted
Postgres: `postgresql+asyncpg://user:pass@host:5432/dbname`. Providers: Neon,
Supabase, Railway. The app auto-converts `postgresql://` to the async driver.

### `REDIS_URL`
Only needed when `RENDER_ASYNC=true` (background renders via Celery). Format:
`redis://localhost:6379`. Required in production for the publisher scheduler
(`tasks.publish_due`) to fire scheduled posts.

---

## AI providers

### `OPENAI_API_KEY` — required for real generation
- **Unlocks:** scripts, storyboards, quality review, trend analysis, agents.
- **Get it:** <https://platform.openai.com/api-keys> → "Create new secret key".
- **Format:** `sk-...`
- **Notes:** Any OpenAI-compatible endpoint (Claude, Groq, Perplexity) works but
  needs a code change (base URL + model) in `app/providers/llm/`.

### `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID`
- **Unlocks:** real voice narration (otherwise a silent mock voice is used).
- **Get it:** <https://elevenlabs.io> → Profile → API keys.
- **Voice id:** pick a voice in the Voice Library and copy its id; the default
  `21m00Tcm4TlvDq8ikWAM` ("Rachel") works out of the box.

### `HIGGSFIELD_API_KEY` / `RUNWAY_API_KEY`
- **Unlocks:** real AI video clips. Without either, Pollinations (free) is used.
- **Higgsfield:** <https://higgsfield.ai> → account → API. Set
  `HIGGSFIELD_VIDEO_MODEL` to a model slug from your catalog
  (e.g. `higgsfield-ai/veo3`).
- **Runway:** <https://dev.runwayml.com> → API keys.
- Precedence: Higgsfield → Runway → Pollinations.

---

## Storage

- `STORAGE_BACKEND=local` (default): files on disk under `STORAGE_DIR`.
- `STORAGE_BACKEND=s3`: MinIO, AWS S3 or Cloudflare R2. Set `S3_ENDPOINT`,
  `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`.
- Media is served through signed URLs (`/storage/{key}?exp=...&sig=...`), never a
  public directory listing.

---

## Social publishing

Each platform is optional. Without its token, that platform falls back to the
**simulated publisher** — jobs are recorded and marked `provider="mock"` so it is
obvious nothing was actually posted.

> Publishing needs to fetch your rendered video. On a local machine the signed URLs
> are not reachable from the internet, so use real tokens only on a public
> deployment with `STORAGE_BACKEND=s3` (or a public base URL).

### YouTube Shorts — `YOUTUBE_ACCESS_TOKEN`
- **Scope:** `https://www.googleapis.com/auth/youtube.upload`.
- **Get it:** Google Cloud Console → enable "YouTube Data API v3" → create an OAuth
  client → complete the consent flow → exchange for an access token.
- **Format:** `ya29...` (expires in ~1 hour; refresh tokens are a future enhancement).

### TikTok — `TIKTOK_ACCESS_TOKEN`
- **Scope:** `video.publish` (Content Posting API).
- **Get it:** <https://developers.tiktok.com> → create an app → request Content
  Posting API access → OAuth flow.
- **Format:** an access token with publish scope.

### Instagram Reels — `META_ACCESS_TOKEN` + `INSTAGRAM_BUSINESS_ACCOUNT_ID`
- **Get them:** Meta for Developers → create an app → add Instagram Graph API.
  Connect an **Instagram Business** account to a Facebook Page.
- `META_ACCESS_TOKEN`: a long-lived token (Instagram content publish permission).
- `INSTAGRAM_BUSINESS_ACCOUNT_ID`: the numeric IG business account id.
- Instagram requires a **publicly reachable** video URL, so S3 storage or a public
  deployment is required for real posts.

### Scheduler
Scheduled posts are published by the Celery beat entry `tasks.publish_due` (every 60s).
Run both a worker and beat in production:
`celery -A app.tasks.celery_app worker` and `celery -A app.tasks.celery_app beat`.

---

## Billing (Stripe)

With no Stripe keys, upgrading a plan runs in **demo mode**: the plan changes
immediately with no charge. That makes the flow testable, and is clearly reported as
`mode: "demo"`.

To go live:
1. `STRIPE_SECRET_KEY` — Stripe Dashboard → Developers → API keys → secret key (`sk_...`).
2. Create a recurring **Price** for the Creator plan → copy its id (`price_...`) into
   `STRIPE_PRICE_PRO`.
3. `STRIPE_WEBHOOK_SECRET` — add a webhook endpoint pointing at
   `https://your-api/api/billing/webhook`, subscribe to
   `checkout.session.completed`, copy the signing secret (`whsec_...`).
   Without this, the webhook endpoint returns 503 and never trusts payloads.

The `/api/billing/upgrade` shortcut is **disabled** automatically once
`STRIPE_SECRET_KEY` is set, so live deployments can only change plans through a paid
checkout or verified webhook.

---

## What still needs code

These are referenced in `.env.example` but not yet implemented:

- Google Gemini image ("Nanobanana"), Canva — extra image/design sources.
- Suno (music) and Deepgram (captions) — `SUNO_API_KEY`, `DEEPGRAM_API_KEY`.
- Perplexity (research) and Luma (3D) — `PERPLEXITY_API_KEY`, `LUMA_API_KEY`.
- LTX-2 via an aggregator (fal.ai / Replicate) — `FAL_API_KEY`, `REPLICATE_API_TOKEN`.
- Resend (transactional email) — `RESEND_API_KEY`.
- OAuth refresh-token flows for the social platforms (tokens currently expire).

Adding any of these means writing a provider adapter under `app/providers/` and
registering it in the router.
