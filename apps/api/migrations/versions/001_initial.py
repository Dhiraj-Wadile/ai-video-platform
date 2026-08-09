"""Initial schema - 15 tables

Revision ID: 001
Revises:
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("role", sa.String(20), server_default="creator"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Projects
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("project_type", sa.String(30), server_default="short_form"),
        sa.Column("platform", sa.String(50)),
        sa.Column("settings_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Scripts
    op.create_table(
        "scripts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("duration", sa.Integer),
        sa.Column("structure_json", JSONB),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Characters
    op.create_table(
        "characters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("appearance", sa.Text),
        sa.Column("personality", sa.Text),
        sa.Column("voice_config_json", JSONB),
        sa.Column("speaking_style", sa.Text),
        sa.Column("catchphrases", JSONB),
        sa.Column("background", sa.Text),
        sa.Column("behavior", sa.Text),
        sa.Column("relationships", JSONB),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Scenes
    op.create_table(
        "scenes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("script_id", UUID(as_uuid=True), sa.ForeignKey("scripts.id")),
        sa.Column("scene_number", sa.Integer, nullable=False),
        sa.Column("duration", sa.Integer, nullable=False),
        sa.Column("narration", sa.Text),
        sa.Column("visual_description", sa.Text),
        sa.Column("camera", sa.String(50)),
        sa.Column("emotion", sa.String(50)),
        sa.Column("background", sa.String(100)),
        sa.Column("music_mood", sa.String(50)),
        sa.Column("sfx", sa.String(50)),
        sa.Column("caption", sa.Text),
        sa.Column("transition", sa.String(50)),
        sa.Column("character_id", UUID(as_uuid=True), sa.ForeignKey("characters.id")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Assets
    op.create_table(
        "assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Generation Jobs
    op.create_table(
        "generation_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("input_json", JSONB),
        sa.Column("output_json", JSONB),
        sa.Column("model", sa.String(100)),
        sa.Column("tokens_in", sa.Integer),
        sa.Column("tokens_out", sa.Integer),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("cost_cents", sa.Integer),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime),
    )

    # Render Jobs
    op.create_table(
        "render_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("progress", sa.Integer, server_default="0"),
        sa.Column("output_url", sa.String(500)),
        sa.Column("format", sa.String(20), server_default="mp4"),
        sa.Column("resolution", sa.String(20), server_default="1080x1920"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime),
    )

    # Publishing Jobs
    op.create_table(
        "publishing_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("external_id", sa.String(255)),
        sa.Column("published_url", sa.String(500)),
        sa.Column("scheduled_at", sa.DateTime),
        sa.Column("published_at", sa.DateTime),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Trends
    op.create_table(
        "trends",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("source", sa.String(100)),
        sa.Column("score", sa.Float),
        sa.Column("metadata_json", JSONB, server_default="{}"),
        sa.Column("discovered_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Video Analytics
    op.create_table(
        "video_analytics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("views", sa.Integer, server_default="0"),
        sa.Column("watch_time_seconds", sa.Integer, server_default="0"),
        sa.Column("retention_json", JSONB),
        sa.Column("likes", sa.Integer, server_default="0"),
        sa.Column("comments", sa.Integer, server_default="0"),
        sa.Column("shares", sa.Integer, server_default="0"),
        sa.Column("saves", sa.Integer, server_default="0"),
        sa.Column("engagement_rate", sa.Float),
        sa.Column("fetched_at", sa.DateTime, server_default=sa.func.now()),
    )

    # AI Insights
    op.create_table(
        "ai_insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("analysis_json", JSONB),
        sa.Column("recommendations_json", JSONB),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Prompt Templates
    op.create_table(
        "prompt_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("encrypted_key", sa.String(500), nullable=False),
        sa.Column("label", sa.String(100)),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # User Sessions
    op.create_table(
        "user_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(500), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("user_sessions")
    op.drop_table("api_keys")
    op.drop_table("prompt_templates")
    op.drop_table("ai_insights")
    op.drop_table("video_analytics")
    op.drop_table("trends")
    op.drop_table("publishing_jobs")
    op.drop_table("render_jobs")
    op.drop_table("generation_jobs")
    op.drop_table("assets")
    op.drop_table("scenes")
    op.drop_table("scripts")
    op.drop_table("characters")
    op.drop_table("projects")
    op.drop_table("users")
