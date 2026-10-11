"""Add quality_reviews and generation_records (Phase 6: QA, cost, lineage)

Revision ID: 004
Revises: 003
Create Date: 2026-09-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match 001: projects.id is UUID on PostgreSQL, so a bare VARCHAR(36) FK here
# fails with an incompatible-types error and the migration cannot be applied at all.
UUIDType = sa.String(36).with_variant(UUID(as_uuid=True), "postgresql")
JSONType = sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "quality_reviews",
        sa.Column("id", UUIDType, primary_key=True),
        sa.Column("project_id", UUIDType, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("breakdown_json", JSONType, nullable=True),
        sa.Column("problems_json", JSONType, nullable=True),
        sa.Column("recommendations_json", JSONType, nullable=True),
        sa.Column("safe_to_publish", sa.Boolean(), nullable=True),
        sa.Column("source", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_quality_reviews_project_id", "quality_reviews", ["project_id"])

    op.create_table(
        "generation_records",
        sa.Column("id", UUIDType, primary_key=True),
        sa.Column("project_id", UUIDType, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("task", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("cost_cents", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("context_json", JSONType, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_generation_records_project_id", "generation_records", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_records_project_id", table_name="generation_records")
    op.drop_table("generation_records")
    op.drop_index("ix_quality_reviews_project_id", table_name="quality_reviews")
    op.drop_table("quality_reviews")