"""Add agents.knowledge_profile for per-agent retrieval behaviour."""

from alembic import op
import sqlalchemy as sa

revision = "004_agent_knowledge_profile"
down_revision = "003_agent_show_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column(
            "knowledge_profile",
            sa.String(length=20),
            nullable=False,
            server_default="auto",
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "knowledge_profile")
