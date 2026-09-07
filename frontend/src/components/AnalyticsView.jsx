import React, { useEffect, useMemo, useState } from 'react'
import WorkflowSidebar from './WorkflowSidebar'

const API_URL = import.meta.env.VITE_ANALYSIS_API_URL || '/api/predict'

function DynamicVisualization({ result, status }) {
  const classes = Array.isArray(result?.classes) ? result.classes : []
  const metrics = Array.isArray(result?.metrics) ? result.metrics : []
  const confidence = typeof result?.confidence === 'number' ? result.confidence : null
  const trace = Array.isArray(result?.trace) ? result.trace : []
  const hasVisualization = classes.length || metrics.length || confidence !== null

  if (result?.status === 'error' || result?.error) {
    return (
      <div className="analysis-summary-placeholder">
        <div>
          <span>Backend error</span>
          <strong>{result.error || 'Analysis request failed.'}</strong>
        </div>
      </div>
    )
  }

  if (!hasVisualization) {
    return (
      <div className="analysis-visual-workspace">
        <div className="analysis-schematic" aria-label="Analysis visualization workspace">
          <div className="schematic-grid">
            {Array.from({ length: 36 }).map((_, i) => <span key={i} className={i % 7 === 0 || i % 11 === 0 ? 'active' : ''} />)}
          </div>
          <div className="schematic-overlay">
            <div className="schematic-title">{status === 'running' ? 'Processing analysis' : 'Analysis workspace'}</div>
            <div className="schematic-subtitle">Task-specific model output is rendered here when the analysis service returns its result.</div>
          </div>
        </div>
        <div className="analysis-summary-placeholder">
          <div><span>Output type</span><strong>Task-dependent</strong></div>
          <div><span>Input driven</span><strong>Uploaded data</strong></div>
          <div><span>AOI</span><strong>Selected region</strong></div>
          <div><span>Confidence</span><strong>When available</strong></div>
        </div>
      </div>
    )
  }

  return (
    <div className="analysis-visual">
      {confidence !== null && (
        <div className="confidence-gauge">
          <div className="gauge-ring" style={{ '--confidence': `${Math.max(0, Math.min(100, confidence * 100))}%` }}>
            <div><strong>{Math.round(confidence * 100)}%</strong><span>confidence</span></div>
          </div>
        </div>
      )}
      {classes.length > 0 && (
        <div className="class-bars">
          {classes.slice(0, 8).map((item) => {
            const value = Number(item.value ?? item.score ?? item.percentage ?? 0)
            const pct = value <= 1 ? value * 100 : value
            return <div className="class-row" key={item.label}><span>{item.label}</span><div><i style={{ width: `${Math.max(0, Math.min(100, pct))}%` }} /></div><b>{pct.toFixed(1)}%</b></div>
          })}
        </div>
      )}
      {metrics.length > 0 && <div className="dynamic-metrics">{metrics.slice(0, 6).map((m) => <div key={m.label}><span>{m.label}</span><strong>{m.value}</strong></div>)}</div>}
      {trace.length > 0 && <div className="trace-mini">{trace.slice(-4).map((item, i) => <div key={i}><span>{item.step || item.name || `Step ${i + 1}`}</span><b>{item.status || 'done'}</b></div>)}</div>}
    </div>
  )
}

export default function AnalyticsView({ files, currentTypeConfig, aoi, task, query, onBack, onViewResults }) {
  const [status, setStatus] = useState('preparing')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState(null)
  const [startedAt] = useState(() => Date.now())
  const [elapsed, setElapsed] = useState(0)

  const stages = useMemo(() => [
    ['Input validation', progress >= 5 ? 'Completed' : 'In progress'],
    ['Image preprocessing', progress >= 20 ? 'Completed' : progress > 5 ? 'In progress' : 'Pending'],
    ['Specialist model execution', progress >= 55 ? 'Completed' : progress >= 20 ? 'In progress' : 'Pending'],
    ['Result aggregation', progress >= 85 ? 'Completed' : progress >= 55 ? 'In progress' : 'Pending'],
  ], [progress])

  useEffect(() => {
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 500)
    return () => clearInterval(timer)
  }, [startedAt])

  useEffect(() => {
    let cancelled = false
    let timer
    const run = async () => {
      setStatus('running')
      setProgress(5)
      timer = setInterval(() => setProgress((p) => Math.min(p + 4, 94)), 350)
      try {
        const form = new FormData()

        // Map the UI task model to the production FastAPI contract.
        // Task 1/2 variants are served by the shared task12 adapter.
        if (task.taskId === 'change') {
          form.append('task', 'task3')
          form.append('before_image', files[0].file, files[0].name)
          form.append('after_image', files[1].file, files[1].name)
        } else if (task.taskId === 'fusion') {
          form.append('task', 'task4')
          form.append('optical_image', files[0].file, files[0].name)
          form.append('sar_image', files[1].file, files[1].name)
        } else {
          form.append('task', 'task12')
          const inputMode =
            currentTypeConfig.id === 'sar'
              ? 'single_sar'
              : 'single_optical'
          form.append('input_mode', inputMode)
          form.append('image', files[0].file, files[0].name)
        }

        form.append('question', query)
        form.append('max_new_tokens', task.taskId === 'change' ? '20' : task.taskId === 'fusion' ? '80' : '128')

        const response = await fetch(API_URL, {
          method: 'POST',
          body: form,
          headers: {
            // Do not put a secret API key in browser code.
            // Authentication belongs at the trusted backend/reverse-proxy boundary.
          },
        })

        const data = await response.json().catch(() => ({}))

        if (!response.ok) {
          throw new Error(
            data?.error || data?.detail || `Analysis request failed (HTTP ${response.status}).`
          )
        }

        if (data?.status === 'error') {
          throw new Error(data.error || 'The analysis service returned an error.')
        }

        if (!cancelled) {
          setResult(data)
          setProgress(100)
          setStatus('completed')
        }
      } catch (error) {
        if (!cancelled) {
          setProgress(100)
          setStatus('error')
          setResult({
            status: 'error',
            answer: '',
            error: error?.message || 'The analysis service could not complete the request.',
          })
        }
      } finally {
        if (timer) clearInterval(timer)
      }
    }
    run()
    return () => { cancelled = true; if (timer) clearInterval(timer) }
  }, [aoi, currentTypeConfig.id, files, query, task.taskId, task.taskLabel])

  const resultPayload = { task, query, aoi, currentTypeConfig, files: files.map((f) => ({ name: f.name, type: f.file?.type, size: f.file?.size, preview: f.preview })), result }

  return (
    <div className="main-content-layout analytics-layout">
      <WorkflowSidebar currentStep={4} />
      <main className="center-workspace">
        <div className="page-header-block">
          <h2 className="page-heading">View Analytics</h2>
          <p className="page-subheading">Observable execution status, workflow details and task-specific analysis output.</p>
        </div>

        <section className="analytics-status-card">
          <div>
            <span className="status-eyebrow">DETECTED TASK TYPE</span>
            <h3>{task.taskLabel}</h3>
            <p>{query}</p>
          </div>
          <div className={`run-status ${status}`}><span />{status === 'running' ? 'Processing' : status === 'error' ? 'Failed' : 'Completed'}</div>
        </section>

        <section className="analytics-meta-grid">
          <div><span>Input configuration</span><strong>{currentTypeConfig.title}</strong><small>{files.length} uploaded image{files.length !== 1 ? 's' : ''}</small></div>
          <div><span>Selected AOI</span><strong>{aoi.width.toFixed(1)}% × {aoi.height.toFixed(1)}%</strong><small>Position {aoi.left.toFixed(1)}%, {aoi.top.toFixed(1)}%</small></div>
          <div><span>Specialist workflow</span><strong>{task.taskLabel}</strong><small>Task-specific processing sequence</small></div>
          <div><span>Elapsed</span><strong>{String(Math.floor(elapsed / 60)).padStart(2, '0')}:{String(elapsed % 60).padStart(2, '0')}</strong><small>Execution time</small></div>
        </section>

        <section className="execution-card">
          <div className="card-heading-row"><h3>Execution sequence</h3><span>{progress}%</span></div>
          <div className="progress-track"><div style={{ width: `${progress}%` }} /></div>
          <div className="stage-list">{stages.map(([name, state]) => <div key={name}><span className={`stage-dot ${state.toLowerCase().replaceAll(' ', '-')}`} /> <strong>{name}</strong><em>{state}</em></div>)}</div>
        </section>

        <section className="analysis-output-card">
          <div className="card-heading-row"><div><h3>Analysis representation</h3><p>Task-specific visualization area for model-generated classes, metrics, confidence, change information or other returned outputs.</p></div><span className="output-badge">{status === 'error' ? 'Request failed' : result ? 'Model output received' : status === 'running' ? 'Processing' : 'Analysis ready'}</span></div>
          <DynamicVisualization result={result} status={status} />
        </section>

        <section className="trace-card">
          <div className="card-heading-row"><h3>Analysis trace</h3><span>{files.length} file{files.length !== 1 ? 's' : ''} submitted</span></div>
          <div className="trace-list">{stages.map(([name, state], i) => <div key={name}><span className="trace-index">{i + 1}</span><div><strong>{name}</strong><small>{state} · task={task.taskId}</small></div></div>)}</div>
        </section>

        <div className="bottom-action-bar">
          <button type="button" className="btn-bottom-reset" onClick={onBack}>← Back: Ask Question</button>
          <button type="button" className="btn-bottom-next ready" onClick={() => onViewResults(resultPayload)}>View Results →</button>
        </div>
      </main>
    </div>
  )
}
