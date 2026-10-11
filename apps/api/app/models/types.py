import uuid as _uuid

from sqlalchemy import String, JSON
from app.config import settings

# Use UUID for PostgreSQL, String for SQLite
USE_POSTGRES = "postgresql" in settings.database_url

if USE_POSTGRES:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB

    class UUIDType(PG_UUID):
        """Postgres uuid column that accepts the string ids used everywhere else in the app.

        Model defaults produce ``str(uuid4())`` and API responses serialize ids as strings, so the
        column coerces on the way in and returns strings on the way out. Without this, the same code
        raises ``invalid input for query argument: expected uuid`` on Postgres while working on SQLite.
        """

        cache_ok = True

        def load_dialect_impl(self, dialect):
            return dialect.type_descriptor(PG_UUID(as_uuid=True))

        def process_bind_param(self, value, dialect):
            if value is not None and not isinstance(value, _uuid.UUID):
                value = _uuid.UUID(str(value))
            return value

        def process_result_value(self, value, dialect):
            return None if value is None else str(value)

    JSONType = JSONB
else:
    # SQLite compatibility
    UUIDType = String(36)
    JSONType = JSON
