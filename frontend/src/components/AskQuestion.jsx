import React, { useEffect, useMemo, useState } from 'react'
import WorkflowSidebar from './WorkflowSidebar'

const baseTasks = [
  { id: 'vqa', label: 'Single-image VQA', needs: 1, allowed: () => true, examples: ['What objects or land-cover features are visible in this image?', 'What is the dominant land-cover type in the selected area?'] },
  { id: 'captioning', label: 'Captioning / scene description', needs: 1, allowed: () => true, examples: ['Describe the scene and the major land-cover features.', 'Generate a concise satellite scene description for this area.'] },
  { id: 'grounding', label: 'Text-guided region grounding', needs: 1, allowed: () => true, examples: ['Locate the built-up area described in the question.', 'Identify and localize the water body in this scene.'] },
  { id: 'change', label: 'Bi-temporal change analysis', needs: 2, allowed: (modality) => modality === 'multitemporal', examples: ['What changed between the two dates in the selected area?', 'Identify significant land-cover changes between the two images.'] },
  { id: 'fusion', label: 'Optical + SAR joint analysis', needs: 2, allowed: (modality) => modality === 'optical_sar', examples: ['What does the optical + SAR combination reveal about this area?', 'Compare information from optical and SAR inputs for this region.'] },
]

export default function AskQuestion({ files, currentTypeConfig, aoi, query, setQuery, taskId, setTaskId, onBack, onSubmit }) {
  const availableTasks = useMemo(() => baseTasks.filter((t) => t.allowed(currentTypeConfig.id)), [currentTypeConfig.id])
  const selectedTask = availableTasks.find((t) => t.id === taskId) || availableTasks[0]
  const [error, setError] = useState('')

  useEffect(() => {
    if (!availableTasks.some((t) => t.id === taskId)) setTaskId(availableTasks[0]?.id || 'vqa')
  }, [availableTasks, taskId, setTaskId])

  const validate = () => {
    if (!selectedTask) return 'Please select an analysis task.'
    if (files.length < selectedTask.needs) return `${selectedTask.label} requires ${selectedTask.needs} uploaded image${selectedTask.needs > 1 ? 's' : ''}.`
    if (!query.trim()) return 'Please enter a natural-language question.'
    if ((selectedTask.id === 'change' || selectedTask.id === 'fusion') && files.length !== 2) return 'This task requires exactly two images. Return to Upload Data and provide the required pair.'
    return ''
  }

  const submit = () => {
    const msg = validate()
    setError(msg)
    if (!msg) onSubmit({ taskId: selectedTask.id, taskLabel: selectedTask.label, query: query.trim() })
  }

  return (
    <div className="main-content-layout ask-layout">
      <WorkflowSidebar currentStep={3} />
      <main className="center-workspace">
        <div className="page-header-block">
          <h2 className="page-heading">Ask Question</h2>
          <p className="page-subheading">Ask the satellite AI a natural-language question about the uploaded data and selected area.</p>
        </div>

        <section className="ask-card">
          <div className="ask-section">
            <label className="field-label">Analysis task</label>
            <select className="task-select" value={selectedTask?.id || ''} onChange={(e) => { setTaskId(e.target.value); setError('') }}>
              {availableTasks.map((task) => <option key={task.id} value={task.id}>{task.label}</option>)}
            </select>
            <div className="config-note">Input: <strong>{currentTypeConfig.title}</strong> · {files.length} image{files.length !== 1 ? 's' : ''} · AOI {aoi.width.toFixed(0)}% × {aoi.height.toFixed(0)}%</div>
          </div>

          <div className="ask-section">
            <label className="field-label">Example questions</label>
            <div className="example-question-list">
              {selectedTask?.examples.map((example) => (
                <button type="button" key={example} className="example-question" onClick={() => { setQuery(example); setError('') }}>{example}</button>
              ))}
            </div>
          </div>

          <div className="ask-section">
            <div className="label-row">
              <label htmlFor="satquery-question" className="field-label">Your question</label>
              <span className="character-count">{query.length}/600</span>
            </div>
            <textarea
              id="satquery-question"
              className="question-input"
              maxLength={600}
              rows={7}
              value={query}
              onChange={(e) => { setQuery(e.target.value); setError('') }}
              placeholder="Type your question here..."
            />
            <div className="question-actions">
              <button type="button" className="text-btn" onClick={() => { setQuery(''); setError('') }} disabled={!query}>Clear</button>
              <button type="button" className="btn-bottom-next ready" onClick={submit}>Submit / Analyse →</button>
            </div>
          </div>

          {error && <div className="validation-error"><strong>Input validation:</strong> {error}</div>}
        </section>

        <div className="bottom-action-bar">
          <button type="button" className="btn-bottom-reset" onClick={onBack}>← Back: Select Area</button>
          <span className="flow-hint">Submit the question to open View Analytics.</span>
        </div>
      </main>
    </div>
  )
}
