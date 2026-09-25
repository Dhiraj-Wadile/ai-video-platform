"""Add progress_message column to render_jobs

Revision ID: 003
Revises: 002
Create Date: 2026-09-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("render_jobs", sa.Column("progress_message", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("render_jobs", "progress_message")