"""Allow full size GitHub Actions run IDs."""

from alembic import op
import sqlalchemy as sa

revision = "0002_github_run_id_bigint"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "workflow_runs",
        "run_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="run_id::bigint",
    )


def downgrade():
    op.alter_column(
        "workflow_runs",
        "run_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="run_id::integer",
    )
