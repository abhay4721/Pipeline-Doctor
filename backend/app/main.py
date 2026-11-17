import hashlib
import hmac
import logging
import time
from datetime import datetime, timezone

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.db import get_db, SessionLocal
from app.models import AnalysisEvidence, FailureAnalysis, IntegrationSetting, Notification, Repository, SuggestedFix, WorkflowJob, WorkflowRun
from app.schemas import ReportRequest
from app.services.analyzer import analyze, sanitize_log
from app.services.github import retrieve_run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("pipeline_doctor")
app = FastAPI(title="Pipeline Doctor API", version="1.0.0", description="CI/CD failure analysis service")
cfg = get_settings()
if cfg.environment.lower() == "production" and (cfg.api_token == "change-me" or "replace-with" in cfg.api_token.lower() or len(cfg.api_token) < 32):
    raise RuntimeError("Set API_TOKEN to a unique value of at least 32 characters in production")
app.add_middleware(CORSMiddleware, allow_origins=[v.strip() for v in cfg.cors_origins.split(",")], allow_credentials=True, allow_methods=["GET", "POST", "PUT", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-GitHub-Event", "X-Hub-Signature-256", "X-GitHub-Delivery"])
_rate_windows: dict[str, list[float]] = {}
_last_rate_cleanup = 0.0


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    global _last_rate_cleanup
    remote_address = request.client.host if request.client else "unknown"
    address = request.headers.get("x-real-ip", remote_address)
    now = time.monotonic()
    if now - _last_rate_cleanup > 300:
        stale = [key for key, stamps in _rate_windows.items() if not stamps or now - stamps[-1] >= 60]
        for key in stale:
            _rate_windows.pop(key, None)
        _last_rate_cleanup = now
    window = [stamp for stamp in _rate_windows.get(address, []) if now - stamp < 60]
    if len(window) >= 120:
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
    window.append(now)
    _rate_windows[address] = window
    return await call_next(request)


def authorize(authorization: str | None):
    expected = "Bearer " + get_settings().api_token
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API token")


def create_analysis(repository: str, run_id: int, db: Session, payload: dict | None = None):
    existing = db.scalar(select(WorkflowRun).join(Repository).where(Repository.full_name == repository, WorkflowRun.run_id == run_id).options(joinedload(WorkflowRun.repository), joinedload(WorkflowRun.analysis)))
    if existing and existing.analysis:
        return existing
    details = payload or retrieve_run(repository, run_id)
    run = details["run"]
    repo = db.scalar(select(Repository).where(Repository.full_name == repository))
    if not repo:
        repo = Repository(full_name=repository)
        db.add(repo)
        db.flush()
    if not existing:
        existing = WorkflowRun(repository=repo, run_id=run_id, workflow_name=run.get("name", "Workflow"), branch=run.get("head_branch", ""), commit_sha=run.get("head_sha", ""), status=run.get("conclusion", "failure") or "failure", html_url=run.get("html_url", ""), actor=(run.get("actor") or {}).get("login", ""), created_at=datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")) if run.get("created_at") else datetime.now(timezone.utc))
        db.add(existing)
        db.flush()
    jobs = details.get("jobs", [])
    for job in jobs:
        if job.get("conclusion") == "failure":
            failed_step = next((s.get("name", "") for s in job.get("steps", []) if s.get("conclusion") == "failure"), "")
            db.add(WorkflowJob(run=existing, name=job.get("name", ""), conclusion=job.get("conclusion", "failure"), failed_step=failed_step))
    output, provider, duration = analyze(details.get("logs", ""))
    analysis = FailureAnalysis(run=existing, failure_type=output["failure_type"], severity=output["severity"], summary=output["summary"], root_cause=output["root_cause"], confidence=output["confidence"], log_excerpt=sanitize_log(details.get("logs", ""))[-6000:], duration_ms=duration, provider=provider)
    analysis.evidence = [AnalysisEvidence(text=e) for e in output.get("evidence", [])]
    analysis.fixes = [SuggestedFix(description=x) for x in output.get("suggested_fixes", [])]
    analysis.debugging_steps = output.get("debugging_steps", [])
    db.add(analysis)
    db.commit()
    db.refresh(existing)
    return existing


def process_run(repository: str, run_id: int):
    db = SessionLocal()
    try:
        details = retrieve_run(repository, run_id)
        if details["run"].get("conclusion") == "success":
            record_success(repository, details["run"])
        elif details["run"].get("conclusion") == "failure":
            create_analysis(repository, run_id, db, details)
    except Exception:
        logger.exception("Failed to analyze %s run %s", repository, run_id)
        db.rollback()
    finally:
        db.close()


def record_success(repository: str, run: dict):
    db = SessionLocal()
    try:
        repo = db.scalar(select(Repository).where(Repository.full_name == repository))
        if not repo:
            repo = Repository(full_name=repository)
            db.add(repo)
            db.flush()
        existing = db.scalar(select(WorkflowRun).where(WorkflowRun.repository_id == repo.id, WorkflowRun.run_id == int(run["id"])))
        if existing:
            return
        db.add(WorkflowRun(repository=repo, run_id=int(run["id"]), workflow_name=run.get("name", "Workflow"), branch=run.get("head_branch", ""), commit_sha=run.get("head_sha", ""), status=run.get("conclusion", "success") or "success", html_url=run.get("html_url", ""), actor=(run.get("actor") or {}).get("login", ""), created_at=datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")) if run.get("created_at") else datetime.now(timezone.utc)))
        db.commit()
    except Exception:
        logger.exception("Failed to record successful run %s", run.get("id"))
        db.rollback()
    finally:
        db.close()


def shape_run(run: WorkflowRun, include_logs: bool = False) -> dict:
    analysis = run.analysis
    if not analysis:
        return {"id": run.id, "run_id": run.run_id, "repository": run.repository.full_name, "workflow_name": run.workflow_name, "branch": run.branch, "commit_sha": run.commit_sha, "status": run.status, "html_url": run.html_url, "actor": run.actor, "created_at": run.created_at, "job_name": run.jobs[0].name if run.jobs else "", "failed_step": run.jobs[0].failed_step if run.jobs else "", "analysis": None}
    result = {"id": run.id, "run_id": run.run_id, "repository": run.repository.full_name, "workflow_name": run.workflow_name, "branch": run.branch, "commit_sha": run.commit_sha, "status": run.status, "html_url": run.html_url, "actor": run.actor, "created_at": run.created_at, "job_name": run.jobs[0].name if run.jobs else "", "failed_step": run.jobs[0].failed_step if run.jobs else "", "analysis": {"id": analysis.id, "failure_type": analysis.failure_type, "severity": analysis.severity, "summary": analysis.summary, "root_cause": analysis.root_cause, "confidence": analysis.confidence, "evidence": [e.text for e in analysis.evidence], "suggested_fixes": [f.description for f in analysis.fixes], "debugging_steps": analysis.debugging_steps or [], "provider": analysis.provider, "duration_ms": analysis.duration_ms}}
    if include_logs:
        result["log_excerpt"] = analysis.log_excerpt
    return result


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
    except Exception as exc:
        raise HTTPException(503, "Database unavailable") from exc
    return {"status": "ok", "service": "pipeline-doctor"}


@app.get("/api/v1/stats")
def stats(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize(authorization)
    total = db.scalar(select(func.count(WorkflowRun.id))) or 0
    failed = db.scalar(select(func.count(WorkflowRun.id)).where(WorkflowRun.status == "failure")) or 0
    successful = db.scalar(select(func.count(WorkflowRun.id)).where(WorkflowRun.status == "success")) or 0
    avg = db.scalar(select(func.avg(FailureAnalysis.duration_ms))) or 0
    rows = db.execute(select(FailureAnalysis.failure_type, func.count(FailureAnalysis.id)).group_by(FailureAnalysis.failure_type)).all()
    return {"total": total, "successful": successful, "failed": failed, "failure_rate": round((failed / total) * 100, 1) if total else 0, "avg_analysis_ms": round(avg), "categories": dict(rows)}


@app.get("/api/v1/runs")
def list_runs(repository: str | None = None, failure_type: str | None = None, severity: str | None = None, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize(authorization)
    stmt = select(WorkflowRun).join(Repository).options(joinedload(WorkflowRun.repository), joinedload(WorkflowRun.analysis).joinedload(FailureAnalysis.evidence), joinedload(WorkflowRun.analysis).joinedload(FailureAnalysis.fixes), joinedload(WorkflowRun.jobs)).order_by(WorkflowRun.created_at.desc()).limit(min(limit, 100)).offset(offset)
    if repository:
        stmt = stmt.where(Repository.full_name.ilike(f"%{repository}%"))
    if failure_type:
        stmt = stmt.where(WorkflowRun.analysis.has(FailureAnalysis.failure_type == failure_type))
    if severity:
        stmt = stmt.where(WorkflowRun.analysis.has(FailureAnalysis.severity == severity))
    return [shape_run(r) for r in db.scalars(stmt).unique().all()]


@app.get("/api/v1/runs/{run_pk}")
def get_run(run_pk: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize(authorization)
    run = db.scalar(select(WorkflowRun).where(WorkflowRun.id == run_pk).options(joinedload(WorkflowRun.repository), joinedload(WorkflowRun.analysis).joinedload(FailureAnalysis.evidence), joinedload(WorkflowRun.analysis).joinedload(FailureAnalysis.fixes), joinedload(WorkflowRun.jobs)))
    if not run:
        raise HTTPException(404, "Run not found")
    return shape_run(run, include_logs=True)


@app.post("/api/v1/reports/run", status_code=202)
def report_run(body: ReportRequest, background: BackgroundTasks, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    authorize(authorization)
    if not get_settings().github_token:
        raise HTTPException(503, "GitHub API token is not configured")
    try:
        background.add_task(process_run, body.repository, body.run_id)
        return {"status": "accepted", "run_id": body.run_id}
    except Exception as exc:
        db.rollback()
        logger.exception("Run report failed")
        raise HTTPException(502, "Could not retrieve or analyze the GitHub workflow run") from exc


@app.post("/api/v1/webhooks/github", status_code=202)
async def github_webhook(request: Request, background: BackgroundTasks, x_hub_signature_256: str | None = Header(default=None), x_github_event: str | None = Header(default=None), x_github_delivery: str | None = Header(default=None), db: Session = Depends(get_db)):
    raw = await request.body()
    if len(raw) > 1_000_000:
        raise HTTPException(413, "Webhook body exceeds the 1 MB limit")
    secret = get_settings().github_webhook_secret
    if not secret:
        raise HTTPException(503, "GitHub webhook secret is not configured")
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not x_hub_signature_256 or not hmac.compare_digest(expected, x_hub_signature_256):
        raise HTTPException(401, "Invalid webhook signature")
    if not x_github_delivery:
        raise HTTPException(400, "Missing delivery ID")
    duplicate = db.scalar(select(IntegrationSetting).where(IntegrationSetting.name == "delivery:" + x_github_delivery))
    if duplicate:
        return {"status": "duplicate"}
    db.add(IntegrationSetting(name="delivery:" + x_github_delivery, value=str(int(time.time()))))
    db.commit()
    if x_github_event == "workflow_run":
        import json
        data = json.loads(raw)
        run = data.get("workflow_run", {})
        repository = data.get("repository", {}).get("full_name")
        if run.get("conclusion") in {"failure", "success"} and repository and run.get("id"):
            if run.get("conclusion") == "failure":
                background.add_task(process_run, repository, int(run["id"]))
            else:
                background.add_task(record_success, repository, run)
            return {"status": "accepted"}
    return {"status": "ignored"}


@app.get("/api/v1/settings")
def settings(authorization: str | None = Header(default=None)):
    authorize(authorization)
    c = get_settings()
    return {"ai_provider": c.ai_provider, "openai_model": c.openai_model, "ollama_model": c.ollama_model, "github_connected": bool(c.github_token), "webhook_configured": bool(c.github_webhook_secret)}
