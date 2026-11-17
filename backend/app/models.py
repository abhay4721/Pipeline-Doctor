from datetime import datetime, timezone

from sqlalchemy import BigInteger, JSON, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def now():
    return datetime.now(timezone.utc)


class Repository(Base):
    __tablename__ = "repositories"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    runs: Mapped[list["WorkflowRun"]] = relationship(back_populates="repository")


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (UniqueConstraint("repository_id", "run_id", name="uq_repository_run"), Index("ix_run_created", "created_at"))
    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), index=True)
    # GitHub Actions run IDs exceed PostgreSQL's signed 32 bit INTEGER range.
    run_id: Mapped[int] = mapped_column(BigInteger)
    workflow_name: Mapped[str] = mapped_column(String(255), default="Workflow")
    branch: Mapped[str] = mapped_column(String(255), default="")
    commit_sha: Mapped[str] = mapped_column(String(64), default="")
    status: Mapped[str] = mapped_column(String(32), default="failed")
    html_url: Mapped[str] = mapped_column(String(1024), default="")
    actor: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    repository: Mapped[Repository] = relationship(back_populates="runs")
    analysis: Mapped["FailureAnalysis | None"] = relationship(back_populates="run", cascade="all, delete-orphan", uselist=False)
    jobs: Mapped[list["WorkflowJob"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class WorkflowJob(Base):
    __tablename__ = "workflow_jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255), default="")
    conclusion: Mapped[str] = mapped_column(String(32), default="failure")
    failed_step: Mapped[str] = mapped_column(String(255), default="")
    run: Mapped[WorkflowRun] = relationship(back_populates="jobs")


class FailureAnalysis(Base):
    __tablename__ = "failure_analyses"
    __table_args__ = (Index("ix_analysis_failure_severity", "failure_type", "severity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_run_id: Mapped[int] = mapped_column(ForeignKey("workflow_runs.id", ondelete="CASCADE"), unique=True, index=True)
    failure_type: Mapped[str] = mapped_column(String(80), default="unknown")
    severity: Mapped[str] = mapped_column(String(24), default="medium")
    summary: Mapped[str] = mapped_column(Text, default="")
    root_cause: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    log_excerpt: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    provider: Mapped[str] = mapped_column(String(40), default="local")
    debugging_steps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    run: Mapped[WorkflowRun] = relationship(back_populates="analysis")
    evidence: Mapped[list["AnalysisEvidence"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    fixes: Mapped[list["SuggestedFix"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class AnalysisEvidence(Base):
    __tablename__ = "analysis_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("failure_analyses.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    analysis: Mapped[FailureAnalysis] = relationship(back_populates="evidence")


class SuggestedFix(Base):
    __tablename__ = "suggested_fixes"
    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("failure_analyses.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text)
    analysis: Mapped[FailureAnalysis] = relationship(back_populates="fixes")


class IntegrationSetting(Base):
    __tablename__ = "integration_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_run_id: Mapped[int | None] = mapped_column(ForeignKey("workflow_runs.id", ondelete="SET NULL"), nullable=True)
    channel: Mapped[str] = mapped_column(String(40), default="github")
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
