import React, { useState } from 'react'
import WorkflowSidebar from './WorkflowSidebar'

export default function AnalyticsHistory({
  history,
  onOpenResult,
  onReuseAnalysis,
  onDeleteHistory,
  onBack,
}) {
  const [selectedSummarySession, setSelectedSummarySession] = useState(null)

  // Trigger report download for a specific history item
  const handleDownloadReport = (item) => {
    const taskLabel = item?.task?.taskLabel || item?.taskLabel || 'Satellite Analysis'
    const queryText = item?.query || 'N/A'
    const resSummary = item?.result?.summary || item?.result?.answer || item?.result?.description || 'Analysis completed.'
    const confVal = typeof item?.result?.confidence === 'number' ? `${Math.round(item.result.confidence <= 1 ? item.result.confidence * 100 : item.result.confidence)}%` : 'N/A'

    const reportText = `========================================================
SATQUERY AI — HISTORICAL ANALYSIS REPORT
========================================================
Session ID: ${item.id}
Date/Time: ${item.timestamp}

1. OVERVIEW
--------------------------------------------------------
Task: ${taskLabel}
Question: ${queryText}
Final Result: ${resSummary}
Confidence: ${confVal}

2. INPUT CONFIGURATION & PARAMETERS
--------------------------------------------------------
Input Configuration: ${item?.currentTypeConfig?.title || item?.inputType || 'Optical'}
Uploaded Images: ${Array.isArray(item?.files) ? item.files.map((f) => f.name).join(', ') : item?.imageName || 'N/A'}
Model Executed: ${item?.result?.modelName || item?.modelName || 'SatQuery Specialist Model v2.5'}
Selected AOI: Left ${item?.aoi?.left?.toFixed(1) || '0'}%, Top ${item?.aoi?.top?.toFixed(1) || '0'}%, Width ${item?.aoi?.width?.toFixed(1) || '0'}%, Height ${item?.aoi?.height?.toFixed(1) || '0'}%

========================================================
`

    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `SatQuery_Report_${item.id}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleDelete = (id) => {
    if (window.confirm('Are you sure you want to delete this analysis session from history?')) {
      onDeleteHistory(id)
    }
  }

  return (
    <div className="main-content-layout analytics-layout">
      <WorkflowSidebar currentStep={6} />
      <main className="center-workspace">
        <div className="page-header-block">
          <h2 className="page-heading">Analytics History</h2>
          <p className="page-subheading">
            Review past satellite image analysis sessions, inspect execution details, re-open results, or reuse past configurations.
          </p>
        </div>

        {history && history.length > 0 ? (
          <div className="history-list">
            {history.map((item) => {
              const fileList = Array.isArray(item.files) ? item.files : []
              const confidence =
                typeof item?.result?.confidence === 'number'
                  ? item.result.confidence
                  : typeof item?.confidence === 'number'
                  ? item.confidence
                  : null

              const shortPreview =
                item?.result?.summary ||
                item?.result?.answer ||
                item?.result?.description ||
                'Analysis executed successfully.'

              return (
                <div className="history-card" key={item.id}>
                  <div className="history-card-header">
                    <div className="history-time-meta">
                      <span className="history-date-badge">{item.timestamp || 'Recent Session'}</span>
                      <span className="history-task-tag">{item?.task?.taskLabel || item?.taskLabel || 'VQA Task'}</span>
                      {confidence !== null && (
                        <span className="history-confidence-pill">
                          {Math.round(confidence <= 1 ? confidence * 100 : confidence)}% confidence
                        </span>
                      )}
                    </div>
                    <span className="history-id-tag">ID: {item.id}</span>
                  </div>

                  <div className="history-card-body">
                    <div className="history-main-info">
                      <div className="history-info-row">
                        <label>Input Type:</label>
                        <span>{item?.currentTypeConfig?.title || item?.inputType || 'Optical Satellite'}</span>
                      </div>
                      <div className="history-info-row">
                        <label>Uploaded Image(s):</label>
                        <span>{fileList.map((f) => f.name).join(', ') || item?.imageName || 'Image'}</span>
                      </div>
                      <div className="history-info-row">
                        <label>Question / Query:</label>
                        <strong className="history-question-text">{item.query || 'N/A'}</strong>
                      </div>
                      <div className="history-info-row preview-row">
                        <label>Result Preview:</label>
                        <p className="history-preview-text">{shortPreview}</p>
                      </div>
                    </div>
                  </div>

                  <div className="history-card-actions">
                    <button
                      type="button"
                      className="btn-history-action open-action"
                      onClick={() => onOpenResult(item)}
                    >
                      Open Result
                    </button>
                    <button
                      type="button"
                      className="btn-history-action summary-action"
                      onClick={() => setSelectedSummarySession(item)}
                    >
                      Execution Summary
                    </button>
                    <button
                      type="button"
                      className="btn-history-action download-action"
                      onClick={() => handleDownloadReport(item)}
                    >
                      Download Report
                    </button>
                    <button
                      type="button"
                      className="btn-history-action reuse-action"
                      onClick={() => onReuseAnalysis(item)}
                    >
                      Reuse Analysis
                    </button>
                    <button
                      type="button"
                      className="btn-history-action delete-action"
                      onClick={() => handleDelete(item.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="empty-history-card">
            <div className="empty-icon-circle">📜</div>
            <h3>No Analytics History Found</h3>
            <p>
              Completed analysis sessions will automatically appear here. Run an analysis to start building your history.
            </p>
          </div>
        )}

        <div className="bottom-action-bar">
          <button type="button" className="btn-bottom-reset" onClick={onBack}>
            ← Back: View Results
          </button>
        </div>

        {/* Execution Summary Modal */}
        {selectedSummarySession && (
          <div className="modal-backdrop" onClick={() => setSelectedSummarySession(null)}>
            <div className="modal-card summary-modal-card" onClick={(e) => e.stopPropagation()}>
              <div className="modal-icon">📋</div>
              <h3>Execution Summary</h3>
              <p>Session ID: {selectedSummarySession.id}</p>

              <div className="summary-details-list">
                <div className="summary-detail-row">
                  <span>Date & Time</span>
                  <strong>{selectedSummarySession.timestamp}</strong>
                </div>
                <div className="summary-detail-row">
                  <span>Selected Task</span>
                  <strong>{selectedSummarySession?.task?.taskLabel || 'N/A'}</strong>
                </div>
                <div className="summary-detail-row">
                  <span>Executed Model</span>
                  <strong>{selectedSummarySession?.result?.modelName || 'SatQuery Specialist Model v2.5'}</strong>
                </div>
                <div className="summary-detail-row">
                  <span>Input Configuration</span>
                  <strong>{selectedSummarySession?.currentTypeConfig?.title || 'Optical'}</strong>
                </div>
                <div className="summary-detail-row">
                  <span>Uploaded Images</span>
                  <strong>
                    {Array.isArray(selectedSummarySession?.files)
                      ? selectedSummarySession.files.map((f) => f.name).join(', ')
                      : 'N/A'}
                  </strong>
                </div>
                <div className="summary-detail-row">
                  <span>Question</span>
                  <strong>{selectedSummarySession.query || 'N/A'}</strong>
                </div>
                <div className="summary-detail-row">
                  <span>AOI Bounds</span>
                  <strong>
                    Left: {selectedSummarySession?.aoi?.left?.toFixed(1) || 0}%, Top:{' '}
                    {selectedSummarySession?.aoi?.top?.toFixed(1) || 0}%, Width:{' '}
                    {selectedSummarySession?.aoi?.width?.toFixed(1) || 0}%, Height:{' '}
                    {selectedSummarySession?.aoi?.height?.toFixed(1) || 0}%
                  </strong>
                </div>
                <div className="summary-detail-row">
                  <span>Result Summary</span>
                  <strong>
                    {selectedSummarySession?.result?.summary ||
                      selectedSummarySession?.result?.answer ||
                      'Completed'}
                  </strong>
                </div>
              </div>

              <button
                type="button"
                className="btn-modal-close"
                onClick={() => setSelectedSummarySession(null)}
              >
                Close Summary
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
