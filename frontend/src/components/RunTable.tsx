import { ArrowRight, GitBranch, Github } from 'lucide-react'
import type { Run } from '../types'

function formatTime(value: string) {
  return new Date(value).toLocaleString([], {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase())
}

type Props = {
  runs: Run[]
  loading: boolean
  onSelect: (run: Run) => void
}

export function RunTable({ runs, loading, onSelect }: Props) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Repository / workflow</th>
            <th>Status</th>
            <th>Failure type</th>
            <th>Branch</th>
            <th>Last run</th>
            <th>Confidence</th>
            <th aria-label="Open run" />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} onClick={() => onSelect(run)} tabIndex={0}
              onKeyDown={(event) => event.key === 'Enter' && onSelect(run)}>
              <td>
                <div className="repo-cell">
                  <span className="repo-icon"><Github size={15} /></span>
                  <span><b>{run.repository}</b><small>{run.workflow_name} · #{run.run_id}</small></span>
                </div>
              </td>
              <td><span className={`status ${run.status === 'success' ? 'passed' : 'failed'}`}>
                <i />{run.status === 'success' ? 'Passed' : run.status}
              </span></td>
              <td>{run.analysis
                ? <span className="type-tag">{titleCase(run.analysis.failure_type)}</span>
                : <span className="muted">Analysis pending</span>}</td>
              <td><span className="branch"><GitBranch size={13} />{run.branch || '—'}</span></td>
              <td className="date-cell">{formatTime(run.created_at)}</td>
              <td>{run.analysis
                ? <span className="confidence"><i><b style={{ width: `${run.analysis.confidence * 100}%` }} /></i>{Math.round(run.analysis.confidence * 100)}%</span>
                : <span className="muted">—</span>}</td>
              <td><ArrowRight className="row-arrow" size={15} /></td>
            </tr>
          ))}
          {!runs.length && (
            <tr><td className="table-empty" colSpan={7}>
              {loading ? 'Loading runs…' : 'No runs match these filters.'}
            </td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
