"""Give prompt templates an owner so one tenant cannot rewrite another's

Revision ID: 005
Revises: 004
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same portable typing as 001/004: uuid on PostgreSQL, TEXT on SQLite.
UUIDType = sa.String(36).with_variant(UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    # SQLite cannot ALTER a table to add a constraint, so batch mode recreates it via
    # copy-and-move; on PostgreSQL it degrades to a plain ALTER.
    with op.batch_alter_table("prompt_templates") as batch:
        batch.add_column(sa.Column("user_id", UUIDType, nullable=True))
        batch.create_foreign_key(
            "fk_prompt_templates_user_id",
            "users",
            ["user_id"],
            ["id"],
        )
        batch.create_index("ix_prompt_templates_user_id", ["user_id"])


def downgrade() -> None:
    with op.batch_alter_table("prompt_templates") as batch:
        batch.drop_index("ix_prompt_templates_user_id")
        batch.drop_constraint("fk_prompt_templates_user_id", type_="foreignkey")
        batch.drop_column("user_id")
