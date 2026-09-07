import React, { useEffect, useMemo, useState } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import RightSidebar from './components/RightSidebar'
import SupportedTypes from './components/SupportedTypes'
import UploadDropzone from './components/UploadDropzone'
import AreaSelection from './components/AreaSelection'
import AskQuestion from './components/AskQuestion'
import AnalyticsView from './components/AnalyticsView'
import ViewResults from './components/ViewResults'
import AnalyticsHistory from './components/AnalyticsHistory'
import { supportedDataTypes } from './data/mockData'

const LOCAL_STORAGE_KEY = 'satquery-analytics-history'

export default function App() {
  const [currentPage, setCurrentPage] = useState('upload')
  const [selectedModality, setSelectedModality] = useState('optical')
  const [files, setFiles] = useState([])
  const [aoi, setAoi] = useState({ left: 23, top: 18, width: 52, height: 58 })
  const [query, setQuery] = useState('')
  const [taskId, setTaskId] = useState('vqa')
  const [errorMessage, setErrorMessage] = useState('')
  const [analysisPayload, setAnalysisPayload] = useState(null)
  const [history, setHistory] = useState([])

  // Load history from localStorage on initial mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (Array.isArray(parsed)) setHistory(parsed)
      }
    } catch (_) {}
  }, [])

  const currentTypeConfig = useMemo(
    () => supportedDataTypes.find((t) => t.id === selectedModality) || supportedDataTypes[0],
    [selectedModality]
  )
  const imagesNeeded = currentTypeConfig.imagesNeeded

  const selectModality = (id) => {
    setSelectedModality(id)
    setErrorMessage('')
    const config = supportedDataTypes.find((t) => t.id === id)
    if (config?.imagesNeeded === 1 && files.length > 1) setFiles(files.slice(0, 1))
    setTaskId(config?.id === 'multitemporal' ? 'change' : config?.id === 'optical_sar' ? 'fusion' : 'vqa')
  }

  const reset = () => {
    files.forEach((f) => f.preview?.startsWith('blob:') && URL.revokeObjectURL(f.preview))
    setFiles([])
    setSelectedModality('optical')
    setAoi({ left: 23, top: 18, width: 52, height: 58 })
    setQuery('')
    setTaskId('vqa')
    setErrorMessage('')
    setCurrentPage('upload')
  }

  const goArea = () => {
    if (files.length !== imagesNeeded) {
      setErrorMessage(
        imagesNeeded === 2
          ? 'Exactly 2 images are required for this input configuration.'
          : 'Please upload exactly 1 image to continue.'
      )
      return
    }
    setErrorMessage('')
    setCurrentPage('area')
  }

  // Handle completion from AnalyticsView -> ViewResults & save session to History
  const handleViewResults = (payload) => {
    const sessionObj = {
      ...payload,
      id: payload.id || `SQ-${Date.now()}`,
      timestamp: payload.timestamp || new Date().toLocaleString(),
    }
    setAnalysisPayload(sessionObj)

    // Save to history state & localStorage
    setHistory((prev) => {
      const filtered = prev.filter((item) => item.id !== sessionObj.id)
      const updated = [sessionObj, ...filtered]
      try {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updated))
      } catch (_) {}
      return updated
    })

    setCurrentPage('results')
  }

  const handleOpenResultFromHistory = (session) => {
    setAnalysisPayload(session)
    setCurrentPage('results')
  }

  const handleReuseAnalysis = (session) => {
    if (session.currentTypeConfig?.id) {
      setSelectedModality(session.currentTypeConfig.id)
    }
    if (session.query) {
      setQuery(session.query)
    }
    if (session.task?.taskId) {
      setTaskId(session.task.taskId)
    }
    if (session.aoi) {
      setAoi(session.aoi)
    }
    setCurrentPage('ask')
  }

  const handleDeleteHistory = (id) => {
    setHistory((prev) => {
      const updated = prev.filter((item) => item.id !== id)
      try {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updated))
      } catch (_) {}
      return updated
    })
  }

  return (
    <div className="satquery-app">
      <Header />
      {currentPage === 'upload' && (
        <div className="main-content-layout">
          <Sidebar />
          <main className="center-workspace">
            <div className="page-header-block">
              <h2 className="page-heading">Upload Satellite Data</h2>
              <p className="page-subheading">
                Upload optical, SAR or paired satellite images to start your analysis.
              </p>
              <div className="images-needed-row">
                <span>Number of images needed</span>
                <b>{imagesNeeded}</b>
                <em>{imagesNeeded === 2 ? '2 images compulsory' : 'Single image only'}</em>
              </div>
            </div>
            <UploadDropzone
              selectedModality={selectedModality}
              imagesNeeded={imagesNeeded}
              files={files}
              onFilesChange={setFiles}
              errorMessage={errorMessage}
              setErrorMessage={setErrorMessage}
            />
            <SupportedTypes selectedModality={selectedModality} onSelectModality={selectModality} />
            <div className="bottom-action-bar">
              <button type="button" className="btn-bottom-reset" onClick={reset}>
                Reset
              </button>
              <button
                type="button"
                className={`btn-bottom-next ${files.length === imagesNeeded ? 'ready' : 'incomplete'}`}
                onClick={goArea}
              >
                Next: Select Area →
              </button>
            </div>
          </main>
          <RightSidebar />
        </div>
      )}

      {currentPage === 'area' && (
        <AreaSelection
          files={files}
          currentTypeConfig={currentTypeConfig}
          aoi={aoi}
          setAoi={setAoi}
          onBack={() => setCurrentPage('upload')}
          onNext={() => setCurrentPage('ask')}
        />
      )}

      {currentPage === 'ask' && (
        <AskQuestion
          files={files}
          currentTypeConfig={currentTypeConfig}
          aoi={aoi}
          query={query}
          setQuery={setQuery}
          taskId={taskId}
          setTaskId={setTaskId}
          onBack={() => setCurrentPage('area')}
          onSubmit={() => setCurrentPage('analytics')}
        />
      )}

      {currentPage === 'analytics' && (
        <AnalyticsView
          files={files}
          currentTypeConfig={currentTypeConfig}
          aoi={aoi}
          task={{
            taskId,
            taskLabel: {
              vqa: 'Single-image VQA',
              captioning: 'Captioning / scene description',
              grounding: 'Text-guided region grounding',
              change: 'Bi-temporal change analysis',
              fusion: 'Optical + SAR joint analysis',
            }[taskId],
          }}
          query={query}
          onBack={() => setCurrentPage('ask')}
          onViewResults={handleViewResults}
        />
      )}

      {currentPage === 'results' && (
        <ViewResults
          payload={analysisPayload}
          onBack={() => setCurrentPage('analytics')}
          onAskAnother={() => setCurrentPage('ask')}
          onAnalyseAnother={() => setCurrentPage('upload')}
          onNextHistory={() => setCurrentPage('history')}
        />
      )}

      {currentPage === 'history' && (
        <AnalyticsHistory
          history={history}
          onOpenResult={handleOpenResultFromHistory}
          onReuseAnalysis={handleReuseAnalysis}
          onDeleteHistory={handleDeleteHistory}
          onBack={() => setCurrentPage('results')}
        />
      )}
    </div>
  )
}
