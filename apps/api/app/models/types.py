from sqlalchemy import String, JSON
from app.config import settings

# Use UUID for PostgreSQL, String for SQLite
USE_POSTGRES = "postgresql" in settings.database_url

if USE_POSTGRES:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
    UUIDType = PG_UUID(as_uuid=True)
    JSONType = JSONB
else:
    # SQLite compatibility
    UUIDType = String(36)
    JSONType = JSON
