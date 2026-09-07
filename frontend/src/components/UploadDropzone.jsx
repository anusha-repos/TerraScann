import React, { useRef, useState } from 'react';

export default function UploadDropzone({
  selectedModality,
  imagesNeeded,
  files,
  onFilesChange,
  errorMessage,
  setErrorMessage,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const slot1InputRef = useRef(null);
  const slot2InputRef = useRef(null);

  const isPairMode = imagesNeeded === 2;

  // Modality specific slot labels
  const slot1Label = selectedModality === 'multitemporal' 
    ? 'Image 1: Reference / Before Date'
    : selectedModality === 'optical_sar'
    ? 'Image 1: Optical Satellite Image'
    : 'Primary Image';

  const slot2Label = selectedModality === 'multitemporal'
    ? 'Image 2: Secondary / After Date'
    : selectedModality === 'optical_sar'
    ? 'Image 2: SAR (Radar) Satellite Image'
    : 'Secondary Image';

  // Process files dropped or chosen
  const handleFiles = (incomingFiles) => {
    setErrorMessage('');
    const validList = Array.from(incomingFiles).filter((f) => {
      const ext = f.name.toLowerCase();
      return (
        f.type.startsWith('image/') ||
        ext.endsWith('.tif') ||
        ext.endsWith('.tiff') ||
        ext.endsWith('.png') ||
        ext.endsWith('.jpg') ||
        ext.endsWith('.jpeg')
      );
    });

    if (validList.length === 0) {
      setErrorMessage('Please select valid satellite image files (.tif, .png, .jpg).');
      return;
    }

    if (!isPairMode) {
      // Single image mode: only allow 1 image
      const file = validList[0];
      const preview = URL.createObjectURL(file);
      onFilesChange([{ file, preview, name: file.name, size: file.size }]);
    } else {
      // Pair mode: allow up to 2 images
      if (validList.length > 2) {
        setErrorMessage('Pair mode requires exactly 2 images. The first 2 files have been selected.');
      }
      
      const newItems = validList.slice(0, 2).map((file) => ({
        file,
        preview: URL.createObjectURL(file),
        name: file.name,
        size: file.size,
      }));

      // If user had 1 file and drops 1 more, combine them up to 2
      if (files.length === 1 && newItems.length === 1) {
        onFilesChange([...files, newItems[0]]);
      } else {
        onFilesChange(newItems);
      }
    }
  };

  // Upload single slot in pair mode
  const handleSlotUpload = (e, slotIndex) => {
    setErrorMessage('');
    const selectedFile = e.target.files && e.target.files[0];
    if (!selectedFile) return;

    const newObj = {
      file: selectedFile,
      preview: URL.createObjectURL(selectedFile),
      name: selectedFile.name,
      size: selectedFile.size,
    };

    const updated = [...files];
    updated[slotIndex] = newObj;
    onFilesChange(updated.filter(Boolean));
    e.target.value = null;
  };

  const removeFile = (index) => {
    const updated = files.filter((_, idx) => idx !== index);
    onFilesChange(updated);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(2)} MB`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  return (
    <div className="upload-section-wrapper">
      {/* Compulsory Pair Notice (Only shown for 2-image modalities) */}
      {isPairMode && (
        <div className="compulsory-alert-banner">
          <div className="alert-badge-icon" aria-hidden="true">!</div>
          <div className="alert-content">
            <strong>2 Images Compulsory:</strong> Multitemporal and Optical+SAR pair analysis require both satellite images to execute spatial and temporal processing.
          </div>
          <div className="compulsory-counter">
            {files.length} / 2 uploaded
          </div>
        </div>
      )}

      {/* Main Drag & Drop Zone */}
      <div
        className={`dropzone-card ${isDragging ? 'dragging' : ''} ${isPairMode ? 'pair-mode' : 'single-mode'}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => {
          if (!isPairMode || files.length === 0) {
            fileInputRef.current && fileInputRef.current.click();
          }
        }}
      >
        <input
          type="file"
          ref={fileInputRef}
          multiple={isPairMode}
          accept=".tif,.tiff,.png,.jpg,.jpeg"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFiles(e.target.files);
              e.target.value = null;
            }
          }}
        />

        <div className="dropzone-icon">
          <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="#087443" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
            <path d="M12 12v9" />
            <path d="m16 16-4-4-4 4" />
          </svg>
        </div>

        <p className="dropzone-text">Drag & drop files here</p>
        <span className="dropzone-or">or</span>

        <button
          type="button"
          className="btn-choose-files"
          onClick={(e) => {
            e.stopPropagation();
            fileInputRef.current && fileInputRef.current.click();
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>{isPairMode ? (files.length === 1 ? 'Choose 2nd File' : 'Choose 2 Files') : 'Choose File'}</span>
        </button>

        <p className="dropzone-meta">
          Maximum file size: 10 MB per file | Supported formats: TIFF, JPG, PNG
        </p>

        {isPairMode ? (
          <p className="mode-indicator compulsory">
            2 images compulsory (upload both at once or individually below)
          </p>
        ) : (
          <p className="mode-indicator single">
            Single image allowed (1 image required for this modality)
          </p>
        )}
      </div>

      {/* Error message banner if any */}
      {errorMessage && (
        <div className="error-toast-banner">
          <span>{errorMessage}</span>
          <button type="button" onClick={() => setErrorMessage('')} aria-label="Dismiss error">×</button>
        </div>
      )}

      {/* Single Mode Preview Card */}
      {!isPairMode && files.length > 0 && (
        <div className="uploaded-list-section">
          <div className="uploaded-file-card">
            <div className="file-preview-thumb">
              <img src={files[0].preview} alt={files[0].name} onError={(e) => { e.target.src = '/images/clean_satellite.png'; }} />
            </div>
            <div className="file-info-details">
              <span className="file-badge-single">1 of 1 Image</span>
              <strong className="file-name-text">{files[0].name}</strong>
              <span className="file-size-text">{formatFileSize(files[0].size)}</span>
            </div>
            <span className="ready-pill">Ready for Analysis</span>
            <button
              type="button"
              className="btn-remove-file"
              onClick={() => removeFile(0)}
              title="Remove image"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Pair Mode 2-Slot Display (Compulsory Uploads) */}
      {isPairMode && (
        <div className="pair-slots-container">
          <input
            type="file"
            ref={slot1InputRef}
            accept=".tif,.tiff,.png,.jpg,.jpeg"
            style={{ display: 'none' }}
            onChange={(e) => handleSlotUpload(e, 0)}
          />
          <input
            type="file"
            ref={slot2InputRef}
            accept=".tif,.tiff,.png,.jpg,.jpeg"
            style={{ display: 'none' }}
            onChange={(e) => handleSlotUpload(e, 1)}
          />

          {/* Slot 1 */}
          <div className={`pair-slot-box ${files[0] ? 'filled' : 'empty'}`}>
            <div className="slot-header">
              <span className="slot-pill">Image 1 (Compulsory)</span>
              <span className="slot-subheading">{slot1Label}</span>
            </div>
            {files[0] ? (
              <div className="slot-content filled">
                <div className="slot-thumb-wrap">
                  <img src={files[0].preview} alt={files[0].name} onError={(e) => { e.target.src = '/images/clean_satellite.png'; }} />
                </div>
                <div className="slot-details">
                  <strong className="file-name-text">{files[0].name}</strong>
                  <span className="file-size-text">{formatFileSize(files[0].size)}</span>
                </div>
                <span className="slot-status-ready">Uploaded</span>
                <button
                  type="button"
                  className="btn-remove-file"
                  onClick={() => removeFile(0)}
                  title="Remove Image 1"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="slot-content empty" onClick={() => slot1InputRef.current && slot1InputRef.current.click()}>
                <span className="slot-empty-icon" aria-hidden="true">+</span>
                <span className="slot-empty-title">Select Image 1</span>
                <span className="slot-empty-subtitle">Click to browse or drop file</span>
              </div>
            )}
          </div>

          {/* Slot 2 */}
          <div className={`pair-slot-box ${files[1] ? 'filled' : 'empty'}`}>
            <div className="slot-header">
              <span className="slot-pill">Image 2 (Compulsory)</span>
              <span className="slot-subheading">{slot2Label}</span>
            </div>
            {files[1] ? (
              <div className="slot-content filled">
                <div className="slot-thumb-wrap">
                  <img src={files[1].preview} alt={files[1].name} onError={(e) => { e.target.src = '/images/sar_images.png'; }} />
                </div>
                <div className="slot-details">
                  <strong className="file-name-text">{files[1].name}</strong>
                  <span className="file-size-text">{formatFileSize(files[1].size)}</span>
                </div>
                <span className="slot-status-ready">Uploaded</span>
                <button
                  type="button"
                  className="btn-remove-file"
                  onClick={() => removeFile(1)}
                  title="Remove Image 2"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="slot-content empty" onClick={() => slot2InputRef.current && slot2InputRef.current.click()}>
                <span className="slot-empty-icon" aria-hidden="true">+</span>
                <span className="slot-empty-title">Select Image 2</span>
                <span className="slot-empty-subtitle">Click to browse or drop file</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}