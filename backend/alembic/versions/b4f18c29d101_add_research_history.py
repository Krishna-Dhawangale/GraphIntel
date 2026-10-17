"""add research history table

Revision ID: b4f18c29d101
Revises: 3c1f9d8a7b62
Create Date: 2026-10-17 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4f18c29d101"
down_revision: Union[str, None] = "3c1f9d8a7b62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "research_history",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("guest_session_id", sa.String(length=64), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("retrieval_mode", sa.String(length=32), server_default="hybrid", nullable=False),
        sa.Column("citations_json", sa.Text(), nullable=True),
        sa.Column("graph_paths_json", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="SUCCESS", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table("research_history") as batch_op:
        batch_op.create_index("ix_research_history_user_id", ["user_id"])
        batch_op.create_index("ix_research_history_guest_session_id", ["guest_session_id"])
        batch_op.create_index("ix_research_history_retrieval_mode", ["retrieval_mode"])
        batch_op.create_index("ix_research_history_created_at", ["created_at"])
        batch_op.create_index("ix_research_history_user_created", ["user_id", "created_at"])
        batch_op.create_index("ix_research_history_guest_created", ["guest_session_id", "created_at"])


def downgrade() -> None:
    op.drop_table("research_history")
