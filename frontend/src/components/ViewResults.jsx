import React from 'react'
import WorkflowSidebar from './WorkflowSidebar'

export default function ViewResults({
  payload,
  onBack,
  onAskAnother,
  onAnalyseAnother,
  onNextHistory,
}) {
  const result = payload?.result || null
  const files = payload?.files || []
  const task = payload?.task || { taskId: 'vqa', taskLabel: 'Single-image VQA' }
  const aoi = payload?.aoi || { left: 23, top: 18, width: 52, height: 58 }
  const currentTypeConfig = payload?.currentTypeConfig || { title: 'Optical Satellite Image' }
  const query = payload?.query || ''
  const modelName = result?.modelName || payload?.modelName || 'SatQuery Specialist Model v2.5'

  const isTwoImages = files.length === 2

  // Extract confidence if available
  const confidence =
    typeof result?.confidence === 'number'
      ? result.confidence
      : typeof payload?.confidence === 'number'
      ? payload.confidence
      : null

  // Extract visual evidence if available
  const visualEvidence = result?.visualEvidence || result?.heatmap || result?.annotatedImage || result?.changeMap || null

  // Helper function to trigger downloading text report
  const handleDownloadReport = () => {
    const reportText = `========================================================
SATQUERY AI — ANALYSIS REPORT
========================================================
Report ID: ${payload?.id || 'SQ-' + Date.now()}
Generated Date: ${new Date().toLocaleString()}

1. ANALYSIS SUMMARY
--------------------------------------------------------
Input Mode: ${isTwoImages ? 'Two Images (Comparison / Pair Analysis)' : 'Single Image Analysis'}
Task Type: ${task.taskLabel}
Question / Query: ${query || 'N/A'}
Final Result: ${result?.summary || result?.answer || result?.description || 'Analysis completed successfully.'}
Confidence: ${confidence !== null ? `${Math.round(confidence <= 1 ? confidence * 100 : confidence)}%` : 'Not available'}

2. INPUT CONFIGURATION & PARAMETERS
--------------------------------------------------------
Input Configuration: ${currentTypeConfig.title}
Uploaded Images (${files.length}): ${files.map((f) => f.name).join(', ') || 'N/A'}
Selected AOI Bounds: Left ${aoi.left.toFixed(1)}%, Top ${aoi.top.toFixed(1)}%, Width ${aoi.width.toFixed(1)}%, Height ${aoi.height.toFixed(1)}%
Model Executed: ${modelName}

3. ${isTwoImages ? 'COMPARISON & CHANGE RESULTS' : 'CAPTION & TASK RESULTS'}
--------------------------------------------------------
${
  isTwoImages
    ? `What Changed: ${result?.whatChanged || result?.summary || 'Temporal/multimodal variation evaluated across image pair.'}\nWhere Changed: AOI (${aoi.left.toFixed(1)}%, ${aoi.top.toFixed(1)}%)\nChange Status: ${result?.changeStatus || 'Increase / Detected'}`
    : `Generated Description / Answer: ${result?.description || result?.answer || result?.summary || 'Scene description generated.'}`
}

========================================================
End of SatQuery AI Report
`

    const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `SatQuery_Report_${payload?.id || Date.now()}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  // Helper for image preview URL resolution
  const getImageSrc = (fileObj, defaultFallback = '/images/clean_satellite.png') => {
    if (fileObj?.preview && typeof fileObj.preview === 'string') return fileObj.preview
    if (fileObj?.src) return fileObj.src
    return defaultFallback
  }

  return (
    <div className="main-content-layout analytics-layout">
      <WorkflowSidebar currentStep={5} />
      <main className="center-workspace">
        <div className="page-header-block">
          <h2 className="page-heading">View Results</h2>
          <p className="page-subheading">
            {isTwoImages
              ? 'Multi-image comparison, temporal change analysis, and spatial evidence.'
              : 'Single-image scene captioning, visual analysis, and feature interpretation.'}
          </p>
        </div>

        {/* 1. Main Final Result Card */}
        <section className="results-card final-answer-card">
          <div className="results-card-header">
            <span className="results-eyebrow">
              {isTwoImages ? 'COMPARISON RESULT' : 'GENERATED CAPTION / DESCRIPTION'}
            </span>
            <span className="task-pill-badge">{task.taskLabel}</span>
          </div>
          <div className="final-answer-body">
            <p className="final-answer-text">
              {result?.summary ||
                result?.answer ||
                result?.description ||
                (isTwoImages
                  ? 'Spatial and structural variations detected between image frames across the selected area of interest.'
                  : query
                  ? `Analysis completed for query: "${query}".`
                  : 'Satellite scene description generated from uploaded satellite data.')}
            </p>
          </div>
        </section>

        {/* 2. Analysed Image Card & Visual Evidence Grid */}
        <div className="results-grid-two-col">
          {/* Analysed Image Card */}
          <section className="results-card image-display-card">
            <div className="results-card-header">
              <h3>{isTwoImages ? 'Image Comparison (Side-by-Side)' : 'Analysed Satellite Image'}</h3>
              <span className="sub-tag">{files.length} Image{files.length !== 1 ? 's' : ''}</span>
            </div>
            <div className="analysed-image-wrapper">
              {isTwoImages ? (
                <div className="dual-results-images">
                  <div className="results-img-box">
                    <img
                      src={getImageSrc(files[0], '/images/clean_satellite.png')}
                      alt={files[0]?.name || 'Image 1 / Before'}
                      className="analysed-img-element"
                      onError={(e) => { e.target.src = '/images/clean_satellite.png' }}
                    />
                    <span className="img-overlay-label">Image 1 / Before: {files[0]?.name || 'Reference'}</span>
                    <div
                      className="results-aoi-box"
                      style={{
                        left: `${aoi.left}%`,
                        top: `${aoi.top}%`,
                        width: `${aoi.width}%`,
                        height: `${aoi.height}%`,
                      }}
                    >
                      <span className="aoi-tag">AOI</span>
                    </div>
                  </div>
                  <div className="results-img-box">
                    <img
                      src={getImageSrc(files[1], '/images/sar_images.png')}
                      alt={files[1]?.name || 'Image 2 / After'}
                      className="analysed-img-element"
                      onError={(e) => { e.target.src = '/images/sar_images.png' }}
                    />
                    <span className="img-overlay-label">Image 2 / After: {files[1]?.name || 'Secondary'}</span>
                    <div
                      className="results-aoi-box"
                      style={{
                        left: `${aoi.left}%`,
                        top: `${aoi.top}%`,
                        width: `${aoi.width}%`,
                        height: `${aoi.height}%`,
                      }}
                    >
                      <span className="aoi-tag">AOI</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="single-results-image">
                  <div className="results-img-box">
                    <img
                      src={getImageSrc(files[0], '/images/clean_satellite.png')}
                      alt={files[0]?.name || 'Analysed Satellite Image'}
                      className="analysed-img-element"
                      onError={(e) => { e.target.src = '/images/clean_satellite.png' }}
                    />
                    <span className="img-overlay-label">{files[0]?.name || 'Analysed Image'}</span>
                    <div
                      className="results-aoi-box"
                      style={{
                        left: `${aoi.left}%`,
                        top: `${aoi.top}%`,
                        width: `${aoi.width}%`,
                        height: `${aoi.height}%`,
                      }}
                    >
                      <span className="aoi-tag">Selected AOI</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* 3. Visual Evidence & Confidence Side Column */}
          <div className="results-side-col">
            {/* Visual Evidence Section */}
            <section className="results-card evidence-card">
              <div className="results-card-header">
                <h3>{isTwoImages ? 'Change Map / Spatial Evidence' : 'Visual Evidence'}</h3>
              </div>
              {visualEvidence ? (
                <div className="visual-evidence-content">
                  <div className="evidence-img-container">
                    <img src={visualEvidence} alt="Spatial Evidence Overlay" className="evidence-img" />
                  </div>
                  <p className="evidence-caption">
                    {isTwoImages ? 'Change map & spatial difference overlay' : 'Annotated feature evidence overlay'}
                  </p>
                </div>
              ) : (
                <div className="no-evidence-box">
                  <span>No visual evidence available.</span>
                </div>
              )}
            </section>

            {/* 4. Confidence Gauge Section (Only shown if confidence score exists) */}
            {confidence !== null && (
              <section className="results-card confidence-card">
                <div className="results-card-header">
                  <h3>Model Confidence</h3>
                </div>
                <div className="confidence-display-row">
                  <div className="gauge-ring-mini" style={{ '--confidence': `${Math.max(0, Math.min(100, (confidence <= 1 ? confidence * 100 : confidence)))}%` }}>
                    <div>
                      <strong>{Math.round(confidence <= 1 ? confidence * 100 : confidence)}%</strong>
                    </div>
                  </div>
                  <div className="confidence-label-wrap">
                    <span className="confidence-status">
                      {confidence >= 0.8 || confidence >= 80 ? 'High Confidence' : confidence >= 0.6 || confidence >= 60 ? 'Moderate Confidence' : 'Standard Confidence'}
                    </span>
                    <small>Calculated across spatial & spectral features</small>
                  </div>
                </div>
              </section>
            )}
          </div>
        </div>

        {/* 5. Task-Specific / Input-Specific Results */}
        <section className="results-card task-specific-card">
          <div className="results-card-header">
            <h3>{isTwoImages ? 'Change Analysis Details' : 'Caption & Task Details'}</h3>
            <span className="task-type-badge">{task.taskLabel}</span>
          </div>

          <div className="task-specific-body">
            {/* TWO IMAGES / COMPARISON MODE */}
            {isTwoImages ? (
              <div className="task-detail-grid three-col">
                <div className="task-detail-block">
                  <label>What Changed</label>
                  <p>{result?.whatChanged || result?.summary || 'Surface cover variation detected between temporal/modal frames.'}</p>
                </div>
                <div className="task-detail-block">
                  <label>Where the Change Occurred</label>
                  <p>{result?.whereChanged || `AOI bounds (${aoi.left.toFixed(1)}%, ${aoi.top.toFixed(1)}%)`}</p>
                </div>
                <div className="task-detail-block">
                  <label>Change Status</label>
                  <span className={`change-status-pill ${(result?.changeStatus || 'Increase').toLowerCase()}`}>
                    {result?.changeStatus || 'Increase / Changed'}
                  </span>
                </div>
              </div>
            ) : (
              /* SINGLE IMAGE MODE */
              <div className="task-detail-grid">
                <div className="task-detail-block">
                  <label>Generated Caption / Description</label>
                  <p>{result?.description || result?.summary || 'Detailed scene description generated from satellite imagery.'}</p>
                </div>
                {query && (
                  <div className="task-detail-block">
                    <label>User Question</label>
                    <p>{query}</p>
                  </div>
                )}
                {task.taskId === 'vqa' && (
                  <div className="task-detail-block">
                    <label>Answer</label>
                    <p>{result?.answer || result?.summary || 'Target evaluated based on image context.'}</p>
                  </div>
                )}
                {task.taskId === 'grounding' && (
                  <div className="task-detail-block">
                    <label>Grounded Region</label>
                    <p>
                      {result?.groundedRegion || `Region identified at Left: ${aoi.left.toFixed(1)}%, Top: ${aoi.top.toFixed(1)}%, Width: ${aoi.width.toFixed(1)}%, Height: ${aoi.height.toFixed(1)}%`}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* 6. Analysis Details */}
        <section className="results-card analysis-details-card">
          <div className="results-card-header">
            <h3>Analysis Details</h3>
          </div>
          <div className="details-table-grid">
            <div className="detail-item">
              <span>Selected Task</span>
              <strong>{task.taskLabel || 'Not available'}</strong>
            </div>
            <div className="detail-item">
              <span>Model Name</span>
              <strong>{modelName || 'Not available'}</strong>
            </div>
            <div className="detail-item">
              <span>Input Type</span>
              <strong>{currentTypeConfig.title || 'Not available'}</strong>
            </div>
            <div className="detail-item">
              <span>Image Name(s)</span>
              <strong className="truncate-text">{files.map((f) => f.name).join(', ') || 'Not available'}</strong>
            </div>
            <div className="detail-item full-row">
              <span>Key Parameters</span>
              <strong>
                AOI Bounds: Left {aoi.left.toFixed(1)}%, Top {aoi.top.toFixed(1)}%, Width {aoi.width.toFixed(1)}%, Height {aoi.height.toFixed(1)}% | Modality: {currentTypeConfig.id || 'N/A'}
              </strong>
            </div>
          </div>
        </section>

        {/* Results Actions Toolbar */}
        <div className="results-actions-bar">
          <div className="actions-left-group">
            <button type="button" className="btn-results-action primary-action" onClick={handleDownloadReport}>
              Download Report
            </button>
            {visualEvidence && (
              <button
                type="button"
                className="btn-results-action secondary-action"
                onClick={() => {
                  const link = document.createElement('a')
                  link.href = visualEvidence
                  link.download = isTwoImages ? 'Change_Map.png' : 'Visual_Evidence.png'
                  link.click()
                }}
              >
                {isTwoImages ? 'Download Change Map' : 'Download Visual Evidence'}
              </button>
            )}
            <button type="button" className="btn-results-action outline-action" onClick={onAskAnother}>
              Ask Another Question
            </button>
            <button type="button" className="btn-results-action outline-action" onClick={onAnalyseAnother}>
              Analyse Another Image
            </button>
          </div>

          <div className="actions-right-group">
            <button type="button" className="btn-bottom-reset" onClick={onBack}>
              ← Back: View Analytics
            </button>
            <button type="button" className="btn-bottom-next ready" onClick={onNextHistory}>
              Next → Analytics History
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
