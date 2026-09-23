"""Add agents.show_sources for per-agent citation visibility."""

from alembic import op
import sqlalchemy as sa

revision = "003_agent_show_sources"
down_revision = "002_document_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("show_sources", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("agents", "show_sources")
