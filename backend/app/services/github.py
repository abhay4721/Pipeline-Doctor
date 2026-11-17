import io
import zipfile

import httpx

from app.core.config import get_settings


def retrieve_run(repository: str, run_id: int) -> dict:
    cfg = get_settings()
    if not cfg.github_token:
        raise ValueError("GITHUB_TOKEN is required to retrieve workflow logs")
    headers = {"Authorization": f"Bearer {cfg.github_token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    base = cfg.github_api_url.rstrip("/")
    with httpx.Client(headers=headers, timeout=45, follow_redirects=True) as client:
        run_resp = client.get(f"{base}/repos/{repository}/actions/runs/{run_id}")
        run_resp.raise_for_status()
        run = run_resp.json()
        jobs_resp = client.get(f"{base}/repos/{repository}/actions/runs/{run_id}/jobs", params={"per_page": 100})
        jobs_resp.raise_for_status()
        jobs = jobs_resp.json().get("jobs", [])
        if run.get("conclusion") != "failure":
            return {"run": run, "jobs": jobs, "logs": ""}
        log_resp = client.get(f"{base}/repos/{repository}/actions/runs/{run_id}/logs")
        log_resp.raise_for_status()
    archive = zipfile.ZipFile(io.BytesIO(log_resp.content))
    combined = []
    for name in archive.namelist():
        if name.lower().endswith(".txt"):
            combined.append(f"--- {name} ---\n{archive.read(name).decode('utf-8', errors='replace')}")
    return {"run": run, "jobs": jobs, "logs": "\n".join(combined)}
