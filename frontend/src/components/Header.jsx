import React from 'react'

export default function Header() {
  return (
    <header className="top-header">
      <div className="brand-container">
        <div className="brand-icon">
          <img src="/images/satquery_logo.png" alt="SatQuery AI" />
        </div>
        <div className="brand-text">
          <h1 className="brand-title">SatQuery AI</h1>
          <p className="brand-subtitle">Vision-Language Assistant</p>
        </div>
      </div>
    </header>
  )
}
