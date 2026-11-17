import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import {
  Activity, AlertTriangle, ArrowLeft, ArrowRight, Check,
  CircleHelp, Clock3, Command, GitBranch, Github, LayoutDashboard,
  LoaderCircle, Search, Settings as SettingsIcon, ShieldCheck,
  TerminalSquare, Workflow,
} from 'lucide-react'
import { RunTable } from './components/RunTable'
const ActivityChart = lazy(() => import('./components/ActivityChart'))
import { clearToken, getDashboard, getRun, getSettings, getToken, healthUrl, setToken } from './services/api'
import type { Run, Settings, Stats } from './types'

type Page = 'overview' | 'history' | 'settings' | 'detail'

const navigation = [
  { id: 'overview' as const, label: 'Overview', icon: LayoutDashboard },
  { id: 'history' as const, label: 'Run history', icon: Activity },
  { id: 'settings' as const, label: 'Settings', icon: SettingsIcon },
]

const blankStats: Stats = {
  total: 0, successful: 0, failed: 0, failure_rate: 0,
  avg_analysis_ms: 0, categories: {},
}

function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

function formatDate(value: string) {
  return new Date(value).toLocaleString([], {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function App() {
  const [token, setTokenState] = useState(getToken)
  const [page, setPage] = useState<Page>('overview')
  const [runs, setRuns] = useState<Run[]>([])
  const [stats, setStats] = useState(blankStats)
  const [settings, setSettings] = useState<Settings | null>(null)
  const [selected, setSelected] = useState<Run | null>(null)
  const [loading, setLoading] = useState(false)
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [failureType, setFailureType] = useState('')
  const [severity, setSeverity] = useState('')
  const [date, setDate] = useState('')
  const [order, setOrder] = useState<'newest' | 'oldest'>('newest')

  async function refresh() {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const dashboard = await getDashboard()
      setRuns(dashboard.runs)
      setStats(dashboard.stats)
      setApiOnline(true)
    } catch (cause) {
      setError((cause as Error).message)
      setApiOnline(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [token])

  useEffect(() => {
    if (page !== 'settings' || !token) return
    getSettings().then(setSettings).catch((cause) => setError((cause as Error).message))
  }, [page, token])

  const filteredRuns = useMemo(() => runs
    .filter((run) => !query || `${run.repository} ${run.workflow_name}`.toLowerCase().includes(query.toLowerCase()))
    .filter((run) => !failureType || run.analysis?.failure_type === failureType)
    .filter((run) => !severity || run.analysis?.severity === severity)
    .filter((run) => !date || new Date(run.created_at).toISOString().slice(0, 10) === date)
    .sort((a, b) => order === 'newest'
      ? new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      : new Date(a.created_at).getTime() - new Date(b.created_at).getTime()),
  [runs, query, failureType, severity, date, order])

  const activity = useMemo(() => Array.from({ length: 7 }, (_, index) => {
    const day = new Date()
    day.setDate(day.getDate() - (6 - index))
    const items = runs.filter((run) => new Date(run.created_at).toDateString() === day.toDateString())
    return {
      day: day.toLocaleDateString([], { weekday: 'short' }),
      failed: items.filter((run) => run.status === 'failure').length,
      passed: items.filter((run) => run.status === 'success').length,
    }
  }), [runs])

  function connect(value: string) {
    setToken(value.trim())
    setTokenState(value.trim())
  }

  async function openRun(run: Run) {
    setSelected(run)
    setPage('detail')
    setDetailLoading(true)
    try {
      setSelected(await getRun(run.id))
    } catch (cause) {
      setError((cause as Error).message)
    } finally {
      setDetailLoading(false)
    }
  }

  function navigate(next: Page) {
    setPage(next)
    if (next !== 'detail') setSelected(null)
  }

  if (!token) return <ConnectScreen onConnect={connect} />

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" onClick={(event) => { event.preventDefault(); navigate('overview') }}>
          <span className="brand-mark"><Activity size={18} /></span>
          <span className="brand-name">Pipeline <b>Doctor</b></span>
          <span className="version-tag">0.1</span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-name"><span><Command size={15} /></span><div><b>Engineering</b><small>GitHub Actions</small></div></div>

        <nav className="navigation" aria-label="Main navigation">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`nav-link ${page === id || (page === 'detail' && id === 'history') ? 'active' : ''}`} onClick={() => navigate(id)}>
              <Icon size={16} /><span>{label}</span>
              {id === 'history' && runs.length > 0 && <small>{runs.length}</small>}
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="connection-state"><i className={apiOnline === false ? 'down' : ''} /><span>{apiOnline === null ? 'Checking API' : apiOnline ? 'API connected' : 'Connection needs attention'}</span></div>
          <div className="profile"><span className="profile-mark">PD</span><span><b>Pipeline Doctor</b><small>Private workspace</small></span></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><b>/</b><strong>{page === 'detail' ? 'Run details' : navigation.find((item) => item.id === page)?.label}</strong></div>
          <div className="topbar-right"><span className="live-indicator"><i className={apiOnline === false ? 'down' : ''} /> API {apiOnline === null ? 'checking' : apiOnline ? 'online' : 'unavailable'}</span><span className="top-avatar">PD</span></div>
        </header>

        <div className="page-content">
          {error && <div className="error-banner"><AlertTriangle size={16} /><span>{error}</span><button onClick={() => void refresh()}>Retry</button></div>}

          {page === 'settings' ? (
            <SettingsPage settings={settings} token={token} onTokenChange={connect} onDisconnect={() => { clearToken(); setTokenState('') }} />
          ) : page === 'detail' && selected ? (
            <RunDetail run={selected} loading={detailLoading} onBack={() => navigate('history')} />
          ) : page === 'history' ? (
            <HistoryPage runs={filteredRuns} allRuns={runs} loading={loading} query={query} setQuery={setQuery}
              failureType={failureType} setFailureType={setFailureType} severity={severity} setSeverity={setSeverity}
              date={date} setDate={setDate} order={order} setOrder={setOrder} onSelect={openRun} />
          ) : (
            <Overview stats={stats} runs={runs} activity={activity} loading={loading} onRefresh={() => void refresh()}
              onHistory={() => navigate('history')} onSettings={() => navigate('settings')} onSelect={openRun} />
          )}
        </div>
      </main>
    </div>
  )
}

function ConnectScreen({ onConnect }: { onConnect: (value: string) => void }) {
  const [value, setValue] = useState('')
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)

  useEffect(() => {
    fetch(healthUrl()).then((response) => setApiOnline(response.ok)).catch(() => setApiOnline(false))
  }, [])

  return (
    <main className="connect-screen">
      <div className="connect-card">
        <div className="connect-brand"><span className="brand-mark"><Activity size={19} /></span><span>Pipeline <b>Doctor</b></span></div>
        <p className="eyebrow">LOCAL WORKSPACE</p>
        <h1>Connect to your API</h1>
        <p className="connect-copy">Use the API token from your environment file. It stays in this browser and is only sent to your Pipeline Doctor server.</p>
        <label htmlFor="api-token">API token</label>
        <input id="api-token" type="password" autoComplete="current-password" value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && value && onConnect(value)} placeholder="Paste API_TOKEN" />
        <button className="button primary wide" disabled={!value.trim()} onClick={() => onConnect(value)}>Connect <ArrowRight size={15} /></button>
        <div className="api-check"><i className={apiOnline ? 'ready' : apiOnline === false ? 'down' : ''} />{apiOnline === null ? 'Checking API…' : apiOnline ? 'API is reachable' : 'API is not reachable at this address'}</div>
      </div>
      <div className="connect-foot">Pipeline Doctor · self-hosted CI run analysis</div>
    </main>
  )
}

function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="page-description">{description}</p></div>{action}</div>
}

function Overview({ stats, runs, activity, loading, onRefresh, onHistory, onSettings, onSelect }: {
  stats: Stats; runs: Run[]; activity: { day: string; failed: number; passed: number }[]; loading: boolean
  onRefresh: () => void; onHistory: () => void; onSettings: () => void; onSelect: (run: Run) => void
}) {
  const lastRun = runs[0]
  const cards = [
    { label: 'Runs recorded', value: stats.total.toLocaleString(), note: 'Across connected workflows', icon: Workflow, kind: 'blue' },
    { label: 'Passed', value: stats.successful.toLocaleString(), note: 'Completed successfully', icon: Check, kind: 'green' },
    { label: 'Failed', value: stats.failed.toLocaleString(), note: 'Runs with a failed conclusion', icon: AlertTriangle, kind: 'red' },
    { label: 'Failure rate', value: `${stats.failure_rate}%`, note: 'Of recorded workflow runs', icon: Activity, kind: 'amber' },
    { label: 'Avg. analysis', value: `${(stats.avg_analysis_ms / 1000).toFixed(1)}s`, note: 'For analyzed failures', icon: Clock3, kind: 'slate' },
  ]

  return <>
    <PageHeading eyebrow="PIPELINE HEALTH / LAST 7 DAYS" title="Overview"
      description={lastRun ? `Latest activity: ${lastRun.repository} · ${formatDate(lastRun.created_at)}` : 'Run history and failure analysis from your connected repositories.'}
      action={<button className="button secondary" onClick={onRefresh}><LoaderCircle className={loading ? 'spin' : ''} size={15} /> Refresh</button>} />

    {!runs.length && !loading && <section className="setup-strip"><span className="setup-icon"><Github size={17} /></span><div><b>No workflow runs yet</b><p>Add the reporter workflow to a repository, or configure a signed GitHub webhook to start collecting run history.</p></div><button className="text-button" onClick={onSettings}>Integration settings <ArrowRight size={14} /></button></section>}

    <section className="metric-grid" aria-label="Pipeline metrics">
      {cards.map(({ label, value, note, icon: Icon, kind }) => <article className="metric-card" key={label}>
        <div className={`metric-icon ${kind}`}><Icon size={16} /></div><p>{label}</p><strong>{value}</strong><small>{note}</small>
      </article>)}
    </section>

    <div className="overview-grid">
      <section className="panel activity-panel">
        <div className="panel-heading"><div><h2>Run activity</h2><p>Completed runs recorded in the last seven days</p></div><span className="range-label"><i /> 7 days</span></div>
        <Suspense fallback={<div className="activity-chart chart-loading">Loading chart…</div>}><ActivityChart data={activity} /></Suspense>
        <div className="chart-legend"><span><i className="failed-dot" /> Failed</span><span><i className="passed-dot" /> Passed</span></div>
      </section>

      <section className="panel category-panel">
        <div className="panel-heading"><div><h2>Failure types</h2><p>From completed analyses</p></div><TerminalSquare size={16} className="panel-mark" /></div>
        {Object.keys(stats.categories).length ? <div className="category-list">
          {Object.entries(stats.categories).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([name, count], index) => <div className="category-row" key={name}>
            <span className={`category-mark mark-${index % 4}`} /><span>{titleCase(name)}</span><b>{count}</b>
          </div>)}
        </div> : <div className="category-empty"><span>—</span><p>Categories will appear after the first failed run is analyzed.</p></div>}
        <button className="text-button category-link" onClick={onHistory}>Browse run history <ArrowRight size={14} /></button>
      </section>
    </div>

    <section className="panel recent-panel">
      <div className="panel-heading"><div><h2>Recent runs</h2><p>Most recently completed workflows</p></div><button className="text-button" onClick={onHistory}>Run history <ArrowRight size={14} /></button></div>
      <RunTable runs={runs.slice(0, 6)} loading={loading} onSelect={onSelect} />
    </section>
    <p className="page-footnote"><ShieldCheck size={14} /> Findings refer to retrieved log lines. Review suggested changes before applying them.</p>
  </>
}

function HistoryPage({ runs, allRuns, loading, query, setQuery, failureType, setFailureType, severity, setSeverity, date, setDate, order, setOrder, onSelect }: {
  runs: Run[]; allRuns: Run[]; loading: boolean; query: string; setQuery: (value: string) => void
  failureType: string; setFailureType: (value: string) => void; severity: string; setSeverity: (value: string) => void
  date: string; setDate: (value: string) => void; order: 'newest' | 'oldest'; setOrder: (value: 'newest' | 'oldest') => void
  onSelect: (run: Run) => void
}) {
  const failureTypes = [...new Set(allRuns.map((run) => run.analysis?.failure_type).filter((value): value is string => Boolean(value)))].sort()
  return <>
    <PageHeading eyebrow="WORKSPACE / RUN HISTORY" title="Run history" description="Search completed runs and narrow results by cause, severity, or date." />
    <section className="panel history-panel">
      <div className="filters">
        <label className="search-field"><Search size={15} /><input aria-label="Search repository or workflow" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Repository or workflow" /></label>
        <select aria-label="Failure type" value={failureType} onChange={(event) => setFailureType(event.target.value)}><option value="">All failure types</option>{failureTypes.map((type) => <option key={type} value={type}>{titleCase(type)}</option>)}</select>
        <select aria-label="Severity" value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">All severities</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
        <label className="date-field"><span>Date</span><input aria-label="Filter by date" type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
        <select aria-label="Sort order" value={order} onChange={(event) => setOrder(event.target.value as 'newest' | 'oldest')}><option value="newest">Newest first</option><option value="oldest">Oldest first</option></select>
      </div>
      <RunTable runs={runs} loading={loading} onSelect={onSelect} />
      <div className="result-count">Showing {runs.length} of {allRuns.length} loaded runs</div>
    </section>
  </>
}

function RunDetail({ run, loading, onBack }: { run: Run; loading: boolean; onBack: () => void }) {
  const analysis = run.analysis
  return <>
    <button className="back-link" onClick={onBack}><ArrowLeft size={14} /> Run history</button>
    <div className="detail-heading"><div><p className="eyebrow">{run.repository} / RUN #{run.run_id}</p><h1>{run.workflow_name}<span className={`run-label ${run.status}`}>{run.status}</span></h1><p className="detail-subtitle"><GitBranch size={14} /> {run.branch || 'no branch'} <span>·</span> {run.commit_sha.slice(0, 8)} <span>·</span> {formatDate(run.created_at)}</p></div>{run.html_url && <a className="button secondary" href={run.html_url} target="_blank" rel="noreferrer"><Github size={15} /> Open run <ArrowRight size={14} /></a>}</div>
    {loading && <div className="detail-loading"><LoaderCircle className="spin" size={16} /> Loading run details…</div>}
    {analysis ? <>
      <div className="detail-grid">
        <section className="panel finding-panel"><div className="finding-label"><Activity size={15} /> FAILURE ANALYSIS <span>{Math.round(analysis.confidence * 100)}% confidence</span></div><h2>{analysis.summary}</h2><p>{analysis.root_cause}</p><div className="finding-tags"><span className="type-tag">{titleCase(analysis.failure_type)}</span><span className={`severity-tag ${analysis.severity}`}>{analysis.severity} severity</span><small>{analysis.provider} · {(analysis.duration_ms / 1000).toFixed(1)}s</small></div></section>
        <section className="panel run-meta"><h2>Run details</h2><Meta label="Workflow" value={run.workflow_name} /><Meta label="Failed job" value={run.job_name || 'Not available'} /><Meta label="Failed step" value={run.failed_step || 'Not identified'} /><Meta label="Triggered by" value={run.actor || 'Not available'} /></section>
      </div>
      <div className="detail-grid lower-detail">
        <section className="panel detail-section"><div className="panel-heading"><div><h2>Suggested checks</h2><p>Review before changing the workflow</p></div></div><ol className="steps">{analysis.suggested_fixes.map((fix, index) => <li key={fix}><span>{index + 1}</span>{fix}</li>)}</ol><h3>Debugging steps</h3><ol className="steps">{analysis.debugging_steps.map((step, index) => <li key={`${index}-${step}`}><span>{index + 1}</span>{step}</li>)}</ol></section>
        <section className="panel detail-section"><div className="panel-heading"><div><h2>Log evidence</h2><p>Evidence is matched against sanitized log lines</p></div><ShieldCheck size={16} className="verified-mark" /></div>{analysis.evidence.length ? <div className="evidence-list">{analysis.evidence.map((line, index) => <div key={`${index}-${line}`}><span>{String(index + 1).padStart(2, '0')}</span><code>{line}</code></div>)}</div> : <div className="uncertain"><CircleHelp size={17} /><p>The cause is uncertain. No log lines could be matched as evidence.</p></div>}{run.log_excerpt && <details className="log-details"><summary>Show sanitized log excerpt</summary><pre>{run.log_excerpt}</pre></details>}</section>
      </div>
    </> : !loading && <section className="panel no-analysis"><CircleHelp size={18} /><p>This run has not been analyzed. It may still be processing or its logs were unavailable.</p></section>}
  </>
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div className="meta-row"><span>{label}</span><b title={value}>{value}</b></div>
}

function SettingsPage({ settings, token, onTokenChange, onDisconnect }: {
  settings: Settings | null; token: string; onTokenChange: (value: string) => void; onDisconnect: () => void
}) {
  const [draft, setDraft] = useState(token)
  const [saved, setSaved] = useState(false)
  return <>
    <PageHeading eyebrow="WORKSPACE / CONFIGURATION" title="Settings" description="Connection status and server-side provider configuration." />
    <section className="panel settings-panel"><div className="settings-heading"><span className="settings-icon"><Command size={16} /></span><div><h2>Dashboard connection</h2><p>The API token is stored in this browser only.</p></div></div>
      <Meta label="API endpoint" value={healthUrl()} />
      <label className="settings-label" htmlFor="settings-token">API token</label><input id="settings-token" type="password" value={draft} onChange={(event) => { setDraft(event.target.value); setSaved(false) }} />
      <div className="settings-actions"><button className="button primary" onClick={() => { onTokenChange(draft); setSaved(true) }}><Check size={14} /> {saved ? 'Saved' : 'Save token'}</button><button className="text-button danger-text" onClick={onDisconnect}>Disconnect</button></div>
    </section>
    <section className="panel settings-panel"><div className="settings-heading"><span className="settings-icon provider-icon"><Activity size={16} /></span><div><h2>Integrations</h2><p>Provider selection and credentials are managed in the server environment.</p></div></div>
      <Meta label="Analysis provider" value={settings?.ai_provider || 'Loading…'} /><Meta label="OpenAI model" value={settings?.openai_model || '—'} /><Meta label="Ollama model" value={settings?.ollama_model || '—'} /><Meta label="GitHub API token" value={settings?.github_connected ? 'Configured' : 'Not configured'} /><Meta label="Webhook signature" value={settings?.webhook_configured ? 'Configured' : 'Not configured'} />
      <p className="settings-note"><ShieldCheck size={15} /> Secret values are never returned by the API.</p>
    </section>
  </>
}
