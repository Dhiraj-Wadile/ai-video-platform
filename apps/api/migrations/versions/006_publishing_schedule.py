"""Add licensing + scheduling fields to publishing_jobs

Revision ID: 006
Revises: 005
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUIDType = sa.String(36).with_variant(UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    # batch mode because SQLite cannot ALTER in place; degrades to plain ALTER on Postgres.
    with op.batch_alter_table("publishing_jobs") as batch:
        batch.add_column(sa.Column("title", sa.String(255), nullable=True))
        batch.add_column(sa.Column("caption", sa.Text(), nullable=True))
        batch.add_column(sa.Column("provider", sa.String(50), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("publishing_jobs") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("provider")
        batch.drop_column("caption")
        batch.drop_column("title")
