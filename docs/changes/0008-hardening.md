# Change 0008 — Hardening: Tenant Isolation, Honest CI, Documentation

**Spec:** `docs/specs/0008-hardening.md`
**Date:** 2026-09-26
**Phase:** 8 — Hardening

## Problem

Phase 7 put real data on screens that used to be static, which turned pre-existing access-control gaps
from invisible into user-visible. Four authenticated endpoints read a row by id without checking who
owns it, and two pieces of project infrastructure were quietly not doing what they claimed:

- **Tenant isolation.** `GET /api/render/status/{job_id}` returned any job's status, error text and
  `output_url`; `GET /api/scripts/{script_id}` returned any project's script;
  `GET /api/analytics/{project_id}` returned any project's metrics; `POST /api/assets/upload` accepted
  a `project_id` it never checked and `GET /api/assets/{key}` minted a URL for any key.
- **401 vs 403.** `HTTPBearer(auto_error=True)` answered `403` for a missing token. The frontend
  treats 401 as "session expired, log out" and anything else as a generic error, so a logged-out user
  got a confusing message instead of a redirect.
- **CI.** The job labelled "Run tests (PostgreSQL)" set `DATABASE_URL` in the environment and
  `tests/conftest.py` overwrote it unconditionally — so the suite ran on SQLite twice and the
  production dialect had never been exercised. The frontend job installed with `npm install` (no
  `npm ci`), never ran the type checker or the vitest suite, and the root `npm run lint` step ran
  `turbo lint`, which depends on `^build` (a full Next build) before linting.
- **UUID columns on Postgres.** `UUIDType` was a bare `PG_UUID(as_uuid=True)` while every model
  default produced `str(uuid4())`. asyncpg is strict about `uuid` parameters, so the first real
  Postgres run would have failed on inserts.
- **Docs.** The README listed 15 tables (17 exist, `quality_reviews` and `generation_records` were
  missing), documented `GET /api/assets` (does not exist), omitted eleven implemented endpoints
  including scene PATCH, quality, costs, lineage, recut and providers, and told you to run
  `npm install` inside `apps/web` in a workspaces monorepo. It also documented `alembic upgrade head`
  as the first step of setup — a command that could not complete on SQLite.

## Changes

### Access control

`app/api/deps.py` (new):

- `owned_project_or_404(db, project_id, user)` — the single ownership predicate. `404` rather than
  `403`, so the API never confirms that someone else's project exists.
- `owned_project_ids(db, user)` — for aggregate queries.
- `project_id_from_asset_key(key)` — parses the `projects/{id}/{type}/{file}` shape produced by
  `storage_service.generate_asset_key`; anything else is not addressable.

Applied to:

| Route | Now |
|---|---|
| `GET /api/render/status/{job_id}` | joins `RenderJob → Project`, requires `Project.user_id == user.id` |
| `GET /api/scripts/{script_id}` | joins `Script → Project`, same rule |
| `GET /api/analytics/{project_id}` | `owned_project_or_404` |
| `GET /api/analytics` | `owned_project_ids` (landed in Phase 7) |
| `POST /api/assets/upload` | `project_id` now **required** (400) and must be owned (404) |
| `GET /api/assets/{key}` | project parsed from the key and verified; unscoped keys 404 |
| `projects.py` | `_owned_project` now delegates to the shared helper (no second copy) |

`app/core/security.py`: `HTTPBearer(auto_error=False)` plus explicit 401s with `WWW-Authenticate`,
so "no token" and "bad token" are both 401 and the frontend logs the user out correctly.

### Config

`config.py`: the default `JWT_SECRET` is now a named constant (`DEFAULT_JWT_SECRET`) and the app logs a
warning at import while it is in use. Development ergonomics are unchanged — a fresh clone still runs
— but the deployment is no longer silently insecure.

### Database portability

`models/types.py`: `UUIDType` on Postgres is a `PG_UUID` subclass that coerces `str → uuid.UUID` on
bind and `uuid.UUID → str` on load. The whole codebase (and every API response) uses string ids, so
both dialects now behave identically at that boundary. Needed before the Postgres CI run could be
trusted; no schema change, so no migration.

`migrations/versions/001_initial.py`: the baseline used `PG_UUID` and `JSONB` unconditionally, so
`alembic upgrade head` — the first command in the README quick start — could not run on SQLite at all
(`Compiler can't render element of type JSONB`). The types are now
`sa.String(36).with_variant(UUID, "postgresql")` and `sa.JSON().with_variant(JSONB, "postgresql")`:
native uuid/JSONB on PostgreSQL, TEXT/JSON on SQLite. Existing PostgreSQL databases are unaffected —
the rendered DDL is identical there.

`alembic check` against a fresh migrated database then surfaced four model/migration drifts, all fixed
on the model side (no data migration, no risk of narrowing a populated column):

- `generation_records.project_id` and `quality_reviews.project_id` are indexed in the schema but not
  declared in the models → added `index=True` (the analytics and quality queries filter on it).
- `projects.status` / `projects.project_type` are `VARCHAR(30)` in the schema, `String(20)` in the
  models → models widened to 30 to match the database.

`alembic check` now reports "No new upgrade operations detected".

### CI

`.github/workflows/ci.yml`:

- `tests/conftest.py` uses `os.environ.setdefault`, so the PostgreSQL job actually runs PostgreSQL.
- Frontend job: `npm ci`, then lint → type-check → `test:run` → build, each with
  `working-directory: apps/web`. (`npm test` is watch mode and is deliberately not used in CI.)

### Docs

README corrected against the code: real AI stack, workspaces install, the product-journey screen
table, 33 routes with ownership semantics, 17 tables, `JWT_SECRET` warning, `STORAGE_BACKEND` /
`RENDER_ASYNC`, and what CI actually runs.

## Verification

- `pytest` — **64 passed** (59 existing + 5 new in `tests/test_security.py`); no test was modified or
  removed.
- `npm run lint`, `npm run type-check`, `npm run test:run` (9 tests), `npm run build` (16 app routes)
  — green.
- `alembic upgrade head` on a fresh SQLite database → 004 (head); `alembic check` → no drift. This did
  not work before this change.
- The PostgreSQL CI run is **not verified locally** — this environment has no Docker daemon. The
  UUID coercion above is reasoned from asyncpg's parameter typing, not executed; the first CI run on
  the branch is the real check.

## Tests

`tests/test_security.py` — two users per scenario, proving isolation rather than just rejection:

- `test_render_status_is_scoped_to_owner` (200 owner / 404 other / 401 anonymous)
- `test_script_read_is_scoped_to_owner`
- `test_analytics_scoped_to_owner` — both users' aggregates, per-video `project_id` lists, and a
  foreign `project_id` returning 404
- `test_assets_are_scoped_to_owner` — own key resolves, foreign key 404, upload into another
  tenant's project 404, missing `project_id` 400
- `test_unscoped_asset_key_is_rejected`

## Deliberately out of scope

- Presigned URLs for S3/MinIO (the current `get_url` builds a key-based URL; keys are `uuid4`-prefixed).
- Rate limiting, RBAC/roles, API-key self-service rotation.
- A frontend error-handling rewrite — the only 401-vs-403 mismatch was fixed at the source.
