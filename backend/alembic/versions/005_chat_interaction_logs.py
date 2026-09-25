"""Chat interaction logs table + agent chat-log toggles."""

from alembic import op
import sqlalchemy as sa

revision = "005_chat_interaction_logs"
down_revision = "004_agent_knowledge_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("chat_log_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "agents",
        sa.Column("chat_log_token", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "agents",
        sa.Column("chat_log_ip", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "agents",
        sa.Column("chat_log_client", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "agents",
        sa.Column("chat_log_agent", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "agents",
        sa.Column("chat_log_question", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "agents",
        sa.Column("chat_log_answer", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "chat_interaction_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("auth_kind", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("token_label", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("api_key_id", sa.String(length=36), nullable=False, server_default=""),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("client", sa.String(length=512), nullable=False, server_default=""),
        sa.Column("agent_name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("question", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer", sa.Text(), nullable=False, server_default=""),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_chat_interaction_logs_timestamp", "chat_interaction_logs", ["timestamp"])
    op.create_index("ix_chat_interaction_logs_agent_id", "chat_interaction_logs", ["agent_id"])
    op.create_index("ix_chat_interaction_logs_session_id", "chat_interaction_logs", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_interaction_logs_session_id", table_name="chat_interaction_logs")
    op.drop_index("ix_chat_interaction_logs_agent_id", table_name="chat_interaction_logs")
    op.drop_index("ix_chat_interaction_logs_timestamp", table_name="chat_interaction_logs")
    op.drop_table("chat_interaction_logs")
    for col in (
        "chat_log_answer",
        "chat_log_question",
        "chat_log_agent",
        "chat_log_client",
        "chat_log_ip",
        "chat_log_token",
        "chat_log_enabled",
    ):
        op.drop_column("agents", col)
