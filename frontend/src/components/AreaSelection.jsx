import React, { useEffect, useRef, useState } from 'react'
import WorkflowSidebar from './WorkflowSidebar'

const DEFAULT_AOI = { left: 23, top: 18, width: 52, height: 58 }

function metrics(rect) {
  const kmW = (rect.width / 100) * 3.2
  const kmH = (rect.height / 100) * 2.1
  const area = kmW * kmH
  const perimeter = 2 * (kmW + kmH)
  return {
    area: `${area.toFixed(2)} km²`,
    perimeter: `${perimeter.toFixed(2)} km`,
    coordinates: `${(16.8452 + (50 - rect.top) * 0.001).toFixed(4)}° N, ${(80.6621 + (rect.left - 50) * 0.001).toFixed(4)}° E`,
  }
}

export default function AreaSelection({ files, currentTypeConfig, aoi, setAoi, onBack, onNext }) {
  const isPair = files.length === 2
  const [zoom, setZoom] = useState(1)
  const mapRefs = useRef([])
  const drag = useRef(null)

  useEffect(() => {
    const move = (e) => {
      const d = drag.current
      if (!d) return
      const dx = e.clientX - d.startX
      const dy = e.clientY - d.startY
      const w = d.mapWidth
      const h = d.mapHeight
      const minW = Math.max(8, 28 / w * 100)
      const minH = Math.max(8, 28 / h * 100)
      let left = d.left, top = d.top, width = d.width, height = d.height
      const px = dx / w * 100
      const py = dy / h * 100

      if (d.mode === 'move') {
        left = Math.max(0, Math.min(100 - width, d.left + px))
        top = Math.max(0, Math.min(100 - height, d.top + py))
      } else {
        if (d.handle.includes('e')) width = Math.max(minW, Math.min(100 - d.left, d.width + px))
        if (d.handle.includes('s')) height = Math.max(minH, Math.min(100 - d.top, d.height + py))
        if (d.handle.includes('w')) {
          const max = d.width - minW
          const delta = Math.max(-d.left, Math.min(max, px))
          left = d.left + delta
          width = d.width - delta
        }
        if (d.handle.includes('n')) {
          const max = d.height - minH
          const delta = Math.max(-d.top, Math.min(max, py))
          top = d.top + delta
          height = d.height - delta
        }
      }
      setAoi({ left, top, width, height })
    }
    const up = () => { drag.current = null }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    return () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
    }
  }, [setAoi])

  const start = (e, mode, handle = null, mapIndex = 0) => {
    e.preventDefault(); e.stopPropagation()
    const el = mapRefs.current[mapIndex]
    if (!el) return
    const r = el.getBoundingClientRect()
    drag.current = { mode, handle, startX: e.clientX, startY: e.clientY, ...aoi, mapWidth: r.width, mapHeight: r.height }
  }

  const reset = () => setAoi({ ...DEFAULT_AOI })
  const currentMetrics = metrics(aoi)

  const renderPane = (item, index, label) => (
    <div className="aoi-pane" ref={(el) => { mapRefs.current[index] = el }}>
      <div className="aoi-pane-header"><span>{label}</span><span className="aoi-file-name">{item?.name || `Image ${index + 1}`}</span></div>
      <div className="aoi-image-wrap">
        {item?.preview ? (
          <img src={item.preview} alt={label} className="aoi-image" style={{ transform: `scale(${zoom})` }} />
        ) : (
          <div className="aoi-image-fallback">Preview unavailable for this file type</div>
        )}
        <div
          className="aoi-box"
          style={{ left: `${aoi.left}%`, top: `${aoi.top}%`, width: `${aoi.width}%`, height: `${aoi.height}%` }}
          onPointerDown={(e) => start(e, 'move', null, index)}
        >
          <span className="aoi-badge">Selected AOI</span>
          {['nw','n','ne','e','se','s','sw','w'].map((h) => (
            <button key={h} type="button" aria-label={`Resize ${h}`} className={`resize-handle ${h}`} onPointerDown={(e) => start(e, 'resize', h, index)} />
          ))}
        </div>
      </div>
    </div>
  )

  return (
    <div className="main-content-layout area-selection-layout">
      <WorkflowSidebar currentStep={2} />
      <main className="center-workspace">
        <div className="page-header-block">
          <h2 className="page-heading">Select Area of Interest</h2>
          <p className="page-subheading">Move the selection or use any edge/corner handle to resize the area.</p>
        </div>

        <div className="aoi-toolbar">
          <button type="button" className="toolbar-btn active">Rectangle selection</button>
          <button type="button" className="toolbar-btn" onClick={reset}>Reset area</button>
          <div className="zoom-controls">
            <button type="button" onClick={() => setZoom((z) => Math.max(.75, z - .25))}>−</button>
            <span>{Math.round(zoom * 100)}%</span>
            <button type="button" onClick={() => setZoom((z) => Math.min(2.5, z + .25))}>+</button>
          </div>
        </div>

        <section className={`aoi-viewer ${isPair ? 'pair-viewer' : 'single-viewer'}`}>
          {renderPane(files[0], 0, isPair ? 'Image 1' : 'Uploaded image')}
          {isPair && renderPane(files[1], 1, 'Image 2')}
        </section>

        <div className="aoi-bottom-grid">
          <div className="aoi-summary-card">
            <div><span>Images</span><strong>{files.length}</strong></div>
            <div><span>Area</span><strong>{currentMetrics.area}</strong></div>
            <div><span>Perimeter</span><strong>{currentMetrics.perimeter}</strong></div>
            <div><span>Center</span><strong>{currentMetrics.coordinates}</strong></div>
          </div>
          <div className="aoi-config-card">
            <span className="muted-label">Input configuration</span>
            <strong>{currentTypeConfig.title}</strong>
            <span>{isPair ? 'Two uploaded images · synchronized AOI' : 'One uploaded image'}</span>
          </div>
        </div>

        <div className="bottom-action-bar">
          <button type="button" className="btn-bottom-reset" onClick={onBack}>← Back: Upload Data</button>
          <button type="button" className="btn-bottom-next ready" onClick={() => onNext(aoi)}>Next: Ask Question →</button>
        </div>
      </main>
    </div>
  )
}
