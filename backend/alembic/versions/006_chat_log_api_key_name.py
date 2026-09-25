"""Add api_key_name to chat_interaction_logs."""

from alembic import op
import sqlalchemy as sa

revision = "006_chat_log_api_key_name"
down_revision = "005_chat_interaction_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_interaction_logs",
        sa.Column("api_key_name", sa.String(length=200), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("chat_interaction_logs", "api_key_name")
