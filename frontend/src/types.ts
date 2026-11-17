export type Analysis = {
  id: number
  failure_type: string
  severity: string
  summary: string
  root_cause: string
  confidence: number
  evidence: string[]
  suggested_fixes: string[]
  debugging_steps: string[]
  provider: string
  duration_ms: number
}

export type Run = {
  id: number
  run_id: number
  repository: string
  workflow_name: string
  branch: string
  commit_sha: string
  status: string
  html_url: string
  actor: string
  created_at: string
  job_name: string
  failed_step: string
  analysis: Analysis | null
  log_excerpt?: string
}

export type Stats = {
  total: number
  successful: number
  failed: number
  failure_rate: number
  avg_analysis_ms: number
  categories: Record<string, number>
}

export type Settings = {
  ai_provider: string
  openai_model: string
  ollama_model: string
  github_connected: boolean
  webhook_configured: boolean
}
