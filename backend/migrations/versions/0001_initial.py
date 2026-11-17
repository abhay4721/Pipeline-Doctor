"""Create the initial Pipeline Doctor schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "repositories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_repositories_full_name", "repositories", ["full_name"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("repository_id", sa.Integer(), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("workflow_name", sa.String(255), nullable=False),
        sa.Column("branch", sa.String(255), nullable=False),
        sa.Column("commit_sha", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("html_url", sa.String(1024), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("repository_id", "run_id", name="uq_repository_run"),
    )
    op.create_index("ix_workflow_runs_repository_id", "workflow_runs", ["repository_id"])
    op.create_index("ix_run_created", "workflow_runs", ["created_at"])

    op.create_table(
        "workflow_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_run_id", sa.Integer(), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("conclusion", sa.String(32), nullable=False),
        sa.Column("failed_step", sa.String(255), nullable=False),
    )
    op.create_index("ix_workflow_jobs_workflow_run_id", "workflow_jobs", ["workflow_run_id"])

    op.create_table(
        "failure_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_run_id", sa.Integer(), sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("failure_type", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(24), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("log_excerpt", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("debugging_steps", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_failure_analyses_workflow_run_id", "failure_analyses", ["workflow_run_id"], unique=True)
    op.create_index("ix_analysis_failure_severity", "failure_analyses", ["failure_type", "severity"])

    op.create_table(
        "analysis_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("failure_analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_index("ix_analysis_evidence_analysis_id", "analysis_evidence", ["analysis_id"])

    op.create_table(
        "suggested_fixes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("failure_analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_index("ix_suggested_fixes_analysis_id", "suggested_fixes", ["analysis_id"])

    op.create_table(
        "integration_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_run_id", sa.Integer(), sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_workflow_run_id", "notifications", ["workflow_run_id"])


def downgrade():
    op.drop_index("ix_notifications_workflow_run_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_table("integration_settings")
    op.drop_index("ix_suggested_fixes_analysis_id", table_name="suggested_fixes")
    op.drop_table("suggested_fixes")
    op.drop_index("ix_analysis_evidence_analysis_id", table_name="analysis_evidence")
    op.drop_table("analysis_evidence")
    op.drop_index("ix_analysis_failure_severity", table_name="failure_analyses")
    op.drop_index("ix_failure_analyses_workflow_run_id", table_name="failure_analyses")
    op.drop_table("failure_analyses")
    op.drop_index("ix_workflow_jobs_workflow_run_id", table_name="workflow_jobs")
    op.drop_table("workflow_jobs")
    op.drop_index("ix_run_created", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_repository_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_repositories_full_name", table_name="repositories")
    op.drop_table("repositories")
