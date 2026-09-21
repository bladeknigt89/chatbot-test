"""Add documents.progress_percent for processing UI."""

from alembic import op
import sqlalchemy as sa

revision = "002_document_progress"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("documents", "progress_percent")
