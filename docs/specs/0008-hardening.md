# Spec 0008: Hardening — Tenant Isolation, CI Truth, Documentation

**Status:** Approved
**Phase:** 8 — Hardening

## Problem

Phase 7 put real data on screens that were previously static, which made pre-existing backend access
control gaps user-visible. Static review of every authenticated route found four endpoints that trust
the caller's id without checking ownership of the row being read:

| Endpoint | Gap | Impact |
|---|---|---|
| `GET /api/render/status/{job_id}` | `RenderJob` fetched by id only | any authenticated user can read any job's status, error text and `output_url` |
| `GET /api/scripts/{script_id}` | `Script` fetched by id only | any authenticated user can read any project's script |
| `GET /api/analytics/{project_id}` | no ownership check | any authenticated user can read any project's metrics |
| `POST /api/assets/upload`, `GET /api/assets/{key}` | `project_id` unvalidated; key not scoped to caller | a user can write into, or mint a URL for, another tenant's prefix |

`GET /api/analytics` leaked across tenants too; that was fixed in Phase 7 because the new screen would
otherwise have displayed it.

Additionally: `JWT_SECRET` ships with a working default value, so a deployment that forgets to set it is
silently forgeable; CI never ran the frontend test suite; and the README documents endpoints, tables and
flows that no longer match the code.

## Non-goals

- No RBAC/roles, no API-key self-service rotation, no signed-URL rework of `S3Storage` (MinIO/S3 keys
  are unguessable `uuid4` prefixes; presigning is a separate phase).
- No rate limiting middleware or new infrastructure.
- No schema changes — every fix is a query-level ownership predicate, so no migration is required.

## Design

### Ownership

Add one shared helper and use it everywhere a row is addressed by id:

```python
# app/api/deps.py
async def owned_project_or_404(db, project_id, user) -> Project
```

- `render/status/{job_id}` → join `RenderJob → Project` and require `Project.user_id == user.id`;
  a foreign or unknown id returns the same `404` as today (no existence oracle).
- `scripts/{script_id}` → join `Script → Project`, same rule.
- `analytics/{project_id}` → reuse the project check.
- `assets/upload` → when `project_id` is supplied it must be owned; the asset key is generated from the
  verified project id. `assets/{key}` → reject keys whose `projects/{project_id}/` prefix is not owned
  by the caller (keys without a project prefix are rejected outright, since nothing generates those).

Unauthenticated access is unchanged: every route still requires `get_current_user`.

### Secrets

`JWT_SECRET` keeps a development default (so a fresh clone runs) but the app logs a loud warning at
startup when the default is in use. Nothing is logged that is not already a constant in the repo.

### CI

The frontend job gains `npm run type-check` and `npm run test:run` alongside lint and build, so the
vitest suite can no longer silently rot. The backend job's "PostgreSQL" run is repaired to actually
use PostgreSQL (`conftest.py` overwrote `DATABASE_URL`), which requires the `str ↔ uuid` column
coercion in `models/types.py` and a dialect-portable baseline migration.

### Migrations

`001_initial.py` hardcoded `postgresql.UUID`/`JSONB`, so the documented `alembic upgrade head` failed
on SQLite. Types become `with_variant(...)` pairs: identical DDL on PostgreSQL, renderable on SQLite.
`alembic check` must then report no drift, which also settles the audit's "Postgres-only baseline
migrations" follow-up.

### Documentation

README is corrected against the code: real route list (including scene PATCH, quality, costs, lineage,
providers, recut), real table list, the async-render flow, the scene-studio journey, and a note that
provider credentials are server-side only.

## Acceptance criteria

1. `GET /api/render/status/{job_id}` returns 404 for another user's job and 200 for the owner's.
2. `GET /api/scripts/{script_id}` returns 404 for another user's script and 200 for the owner's.
3. `GET /api/analytics/{project_id}` returns 404 for another user's project.
4. `GET /api/analytics` totals include only the caller's projects.
5. `POST /api/assets/upload` with a foreign `project_id` → 404; `GET /api/assets/{foreign key}` → 404.
6. All existing tests still pass; no test removed.
7. CI runs frontend lint + type-check + test + build.
8. README matches the implemented routes/tables.
9. `pytest`, `npm run lint`, `npm run type-check`, `npm run test:run`, `npm run build` all green.
10. `alembic upgrade head` applies cleanly on a fresh database and `alembic check` reports no drift.

## Tests

`tests/test_security.py` — one test per row in the table above, each with two users to prove isolation,
plus an unauthenticated check (401).

## Verification

- Backend: `python -m pytest` (SQLite) green; Postgres run unchanged in CI.
- Frontend: lint / type-check / test:run / build green.
- Docs: `docs/changes/0008-hardening.md`; audit phase table → done.
