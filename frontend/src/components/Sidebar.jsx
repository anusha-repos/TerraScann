import React from 'react'

export default function Sidebar() {
  return (
    <aside className="left-sidebar">
      <div className="sidebar-menu">
        <div className="sidebar-item active">Upload Data</div>
      </div>
      <div className="sidebar-card tip-card">
        <div className="tip-header"><span className="tip-title">Tip</span></div>
        <p className="tip-body">For best results, upload clear and recent satellite images with minimum cloud cover.</p>
      </div>
    </aside>
  )
}
