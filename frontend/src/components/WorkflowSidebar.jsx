import React from 'react'

const steps = [
  ['1', 'Upload Data'],
  ['2', 'Select Area'],
  ['3', 'Ask Question'],
  ['4', 'View Analytics'],
  ['5', 'View Results'],
  ['6', 'Analytics History'],
]

export default function WorkflowSidebar({ currentStep }) {
  return (
    <aside className="workflow-sidebar">
      <div className="sidebar-card workflow-card">
        <div className="workflow-title">WORKFLOW</div>
        <div className="workflow-steps">
          {steps.map(([number, label], index) => {
            const step = index + 1
            const state = step < currentStep ? 'completed' : step === currentStep ? 'active' : 'pending'
            return (
              <React.Fragment key={number}>
                <div className={`workflow-row ${state}`}>
                  <div className="workflow-circle">
                    {state === 'completed' ? '✓' : number}
                  </div>
                  <div>
                    <div className="workflow-label">{number}. {label}</div>
                    <div className="workflow-status">
                      {state === 'completed' ? 'Completed' : state === 'active' ? 'In Progress' : 'Pending'}
                    </div>
                  </div>
                </div>
                {index < steps.length - 1 && <div className={`workflow-connector ${step < currentStep ? 'completed' : ''}`} />}
              </React.Fragment>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
