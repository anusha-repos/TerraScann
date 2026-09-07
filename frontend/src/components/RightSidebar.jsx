import React from 'react'

export default function RightSidebar() {
  return (
    <aside className="right-sidebar">
      <div className="sidebar-card guidelines-card">
        <h3 className="sidebar-card-title"><span>Upload Guidelines</span></h3>
        <ul className="guidelines-list">
          <li><span className="bullet-check">✓</span><span>Use clear images with minimum cloud cover.</span></li>
          <li><span className="bullet-check">✓</span><span>For change detection, upload images from different dates.</span></li>
          <li><span className="bullet-check">✓</span><span>For optical + SAR analysis, upload one optical and one SAR image.</span></li>
          <li><span className="bullet-check">✓</span><span>Georeferenced images provide better spatial analysis.</span></li>
        </ul>
      </div>
      <div className="sidebar-card example-card">
        <h3 className="sidebar-card-title"><span>Example: Agriculture Field</span></h3>
        <div className="example-image-container">
          <img src="/images/agriculture_example.png" alt="Agriculture satellite example" className="example-image" />
        </div>
      </div>
    </aside>
  )
}
