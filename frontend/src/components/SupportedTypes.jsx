import React from 'react';
import { supportedDataTypes } from '../data/mockData';

export default function SupportedTypes({ selectedModality, onSelectModality }) {
  return (
    <div className="supported-types-section">
      <h3 className="section-heading">Supported Data Types</h3>
      <div className="types-grid">
        {supportedDataTypes.map((type) => {
          const isSelected = selectedModality === type.id;
          const isPair = type.imagesNeeded === 2;

          return (
            <div
              key={type.id}
              className={`type-card ${isSelected ? 'selected' : ''}`}
              onClick={() => onSelectModality(type.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectModality(type.id);
                }
              }}
            >
              <div className="type-card-top">
                <span className={`type-badge badge-${type.id}`}>{type.badge}</span>
                {isSelected && (
                  <span className="selected-check">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#087443" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </span>
                )}
              </div>

              <div className="type-img-wrapper">
                <img
                  src={type.image}
                  alt={type.title}
                  className="type-thumb"
                  onError={(e) => {
                    e.target.src = '/images/clean_satellite.png';
                  }}
                />
                {isPair && (
                  <div className="split-indicator-overlay">
                    <div className="split-divider-line"></div>
                    <div className="split-handle-circle">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="15 18 9 12 15 6" />
                      </svg>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="9 18 15 12 9 6" />
                      </svg>
                    </div>
                  </div>
                )}
              </div>

              <h4 className="type-title">{type.title}</h4>
              <p className="type-desc">{type.description}</p>

              <div className="type-card-footer">
                <span className={`req-badge ${isPair ? 'compulsory' : 'single'}`}>
                  {isPair ? '2 Images Compulsory' : '1 Single Image'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}