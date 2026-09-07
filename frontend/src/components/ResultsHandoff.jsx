import React, { useEffect, useState } from 'react'
import WorkflowSidebar from './WorkflowSidebar'

export default function ResultsHandoff({ payload, onBack }) {
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (payload) {
      sessionStorage.setItem('satquery-analysis-output', JSON.stringify(payload))
      setSaved(true)
    }
  }, [payload])

  return (
    <div className="main-content-layout analytics-layout">
      <WorkflowSidebar currentStep={5} />
      <main className="center-workspace">
        <div className="page-header-block">
          <h2 className="page-heading">View Results</h2>
          <p className="page-subheading">The analysis package has been carried forward from View Analytics and is ready for the Results interface.</p>
        </div>
        <section className="results-handoff-card">
          <div className="handoff-icon">✓</div>
          <h3>Analysis output transferred</h3>
          <p>{saved ? 'The task, uploaded-image references, question, AOI and model output are available to the next Results page.' : 'Preparing the analysis package for the next Results page.'}</p>
          <div className="handoff-meta">
            <span><b>Task</b>{payload?.task?.taskLabel || '—'}</span>
            <span><b>Images</b>{payload?.files?.length ?? 0}</span>
            <span><b>Question</b>{payload?.query || '—'}</span>
          </div>
        </section>
        <div className="bottom-action-bar">
          <button type="button" className="btn-bottom-reset" onClick={onBack}>← Back: View Analytics</button>
        </div>
      </main>
    </div>
  )
}
