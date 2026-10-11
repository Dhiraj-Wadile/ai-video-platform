"""Add subscription plan fields to users

Revision ID: 007
Revises: 006
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        # server_default so existing rows get "free" instead of NULL (column is NOT NULL).
        batch.add_column(
            sa.Column("plan", sa.String(20), nullable=False, server_default="free")
        )
        batch.add_column(sa.Column("stripe_customer_id", sa.String(255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("stripe_customer_id")
        batch.drop_column("plan")
