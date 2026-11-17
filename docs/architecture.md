# Architecture

## Request and analysis flow

```text
GitHub Actions workflow_run
        │ (repository + run ID, or signed event)
        ▼
FastAPI authentication / HMAC validation / delivery deduplication
        ▼
Background task ── GitHub REST API (metadata, failed jobs, ZIP logs)
        ▼
Secret redaction ── local rules or OpenAI/Ollama structured analysis
        ▼
Evidence validation ── PostgreSQL ── authenticated dashboard API ── React UI
```

The reporter sends only an owner/repository pair and numeric run ID. The API obtains metadata and logs using the server-side GitHub token. A GitHub webhook is separately authenticated using GitHub's `X-Hub-Signature-256`; `X-GitHub-Delivery` prevents a delivery from being processed twice. Successful runs are stored as run metadata; failed runs also receive an analysis.

## Backend modules

- `app/main.py`: HTTP API, authentication, webhook checks, rate limit, persistence orchestration, and background tasks.
- `app/services/github.py`: authenticated GitHub API access and ZIP log extraction.
- `app/services/analyzer.py`: secret cleanup, local signature classification, configurable OpenAI/Ollama calls, schema defaults, and evidence verification.
- `app/models.py`: SQLAlchemy relational schema.
- `migrations/`: Alembic schema history.

The local provider is deterministic and requires no model runtime. OpenAI and Ollama providers are selected with `AI_PROVIDER`; if the selected service is unavailable or returns invalid JSON, the analyzer falls back to local rules. Evidence returned by a model is retained only if it exactly matches a sanitized log line. The model cannot run commands and suggested changes are for human review.

## Data model

`Repository` owns `WorkflowRun` records. A run has jobs and, for failures, one `FailureAnalysis`. Analyses have many evidence lines and suggested fixes. Integration settings also store webhook delivery IDs for replay deduplication. `Users` and `Notifications` tables reserve data shape for future identity and outbound notification features; shared bearer token auth is used in this version.

## Runtime boundaries

- PostgreSQL persists records; SQLite is available for local development.
- FastAPI background tasks make setup lightweight. They are in-process and not durable across process termination. A Celery/Redis worker is the next deployment step for multi-instance or high-volume installations.
- The API rate limit is in-process and per client address. Put a shared rate limiter at the gateway when scaling beyond one process.
- The React app gets stats and history from the API; it has no seeded dashboard data.
- Credentials are provided as environment variables and are never returned by the settings endpoint.
