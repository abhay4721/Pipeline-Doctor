from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AnalysisOut(BaseModel):
    id: int
    failure_type: str
    severity: str
    summary: str
    root_cause: str
    confidence: float
    evidence: list[str]
    suggested_fixes: list[str]
    debugging_steps: list[str]
    provider: str
    duration_ms: int
    model_config = ConfigDict(from_attributes=True)


class RunOut(BaseModel):
    id: int
    run_id: int
    repository: str
    workflow_name: str
    branch: str
    commit_sha: str
    status: str
    html_url: str
    actor: str
    created_at: datetime
    job_name: str = ""
    failed_step: str = ""
    analysis: AnalysisOut | None = None


class StatsOut(BaseModel):
    total: int
    successful: int
    failed: int
    failure_rate: float
    avg_analysis_ms: int
    categories: dict[str, int]


class ReportRequest(BaseModel):
    repository: str = Field(min_length=3, max_length=255, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    run_id: int = Field(gt=0)
