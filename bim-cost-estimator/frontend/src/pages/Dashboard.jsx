import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import toast, { Toaster } from 'react-hot-toast';
import { uploadIFC, extractData, listProjects } from '../services/api';

export default function Dashboard({ projectData, setProjectData, onProjectLoaded }) {
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(projectData ? 'ready' : 'upload');
  const [uploadProgress, setUploadProgress] = useState(0);

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setLoading(true);
    setStep('uploading');
    try {
      toast.loading('Uploading IFC file...', { id: 'upload' });
      setUploadProgress(30);
      const uploadResult = await uploadIFC(file);
      setUploadProgress(60);
      toast.loading('Extracting BIM data...', { id: 'upload' });

      const extractResult = await extractData(uploadResult.project_id, true);
      setUploadProgress(100);

      const data = {
        projectId: uploadResult.project_id,
        filename: uploadResult.filename,
        fileSizeMb: uploadResult.file_size_mb,
        totalElements: extractResult.total_elements,
        elementTypes: extractResult.element_types,
        materials: extractResult.materials,
        storeys: extractResult.storeys,
        elements: extractResult.elements,
      };

      setProjectData(data);
      if (onProjectLoaded) onProjectLoaded(data);
      setStep('ready');
      toast.success(`Project loaded — ${data.totalElements} elements extracted`, { id: 'upload' });
    } catch (err) {
      toast.error(err.message || 'Upload failed', { id: 'upload' });
      setStep('upload');
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  }, [setProjectData, onProjectLoaded]);

  const loadSyntheticDemo = async () => {
    setLoading(true);
    try {
      toast.loading('Generating synthetic demo data...', { id: 'demo' });
      const uploadResult = await uploadIFC(new File([''], 'demo.ifc'), 'Demo Project');
      const extractResult = await extractData(uploadResult.project_id, true);

      const data = {
        projectId: uploadResult.project_id,
        filename: 'demo.ifc',
        fileSizeMb: 0,
        totalElements: extractResult.total_elements,
        elementTypes: extractResult.element_types,
        materials: extractResult.materials,
        storeys: extractResult.storeys,
        elements: extractResult.elements,
      };

      setProjectData(data);
      if (onProjectLoaded) onProjectLoaded(data);
      setStep('ready');
      toast.success('Demo project loaded!', { id: 'demo' });
    } catch (err) {
      toast.error(err.message || 'Failed to load demo', { id: 'demo' });
    } finally {
      setLoading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/octet-stream': ['.ifc', '.ifczip'] },
    maxFiles: 1,
  });

  return (
    <div className="fade-in">
      <Toaster position="top-right" toastOptions={{
        style: { background: '#1a1f35', color: '#f1f5f9', border: '1px solid #1e293b', fontSize: '13px' }
      }} />

      {step !== 'ready' ? (
        <UploadSection
          getRootProps={getRootProps}
          getInputProps={getInputProps}
          isDragActive={isDragActive}
          loading={loading}
          uploadProgress={uploadProgress}
          onLoadDemo={loadSyntheticDemo}
        />
      ) : (
        <ProjectOverview data={projectData} />
      )}
    </div>
  );
}

// ─── Upload Section ─────────────────────────────────────────────────
function UploadSection({ getRootProps, getInputProps, isDragActive, loading, uploadProgress, onLoadDemo }) {
  return (
    <div style={{ maxWidth: 700, margin: '40px auto' }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px' }}>
          BIM Cost & Time Estimator
        </h1>
        <p style={{ color: 'var(--text-muted)', marginTop: 8 }}>
          Upload an IFC file to begin AI-driven construction analysis
        </p>
      </div>

      <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
        <input {...getInputProps()} />
        <div className="dropzone-icon">🏗️</div>
        <div className="dropzone-text">
          {isDragActive ? 'Drop your IFC file here' : 'Drag & drop an IFC file or click to browse'}
        </div>
        <div className="dropzone-hint">.ifc or .ifczip — up to 500 MB</div>
      </div>

      {uploadProgress > 0 && (
        <div className="mt-2">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
          </div>
        </div>
      )}

      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <span className="text-muted text-sm" style={{ marginRight: 12 }}>or</span>
        <button className="btn btn-secondary btn-sm" onClick={onLoadDemo} disabled={loading}>
          🔬 Load Synthetic Demo
        </button>
      </div>
    </div>
  );
}

// ─── Project Overview ───────────────────────────────────────────────
function ProjectOverview({ data }) {
  if (!data) return null;

  const topTypes = Object.entries(data.elementTypes || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  const totalElements = data.totalElements || 0;
  const uniqueMaterials = data.materials?.length || 0;
  const totalStoreys = data.storeys?.length || 0;
  const uniqueTypes = Object.keys(data.elementTypes || {}).length;

  return (
    <div className="slide-up">
      <div className="section-header">
        <div>
          <h2 className="section-title">📊 Project Overview</h2>
          <p className="section-subtitle">
            {data.filename} — Project {data.projectId?.slice(0, 8)}
          </p>
        </div>
        <div className="btn-group">
          <span className="badge badge-success">✓ Data Loaded</span>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="stats-grid stagger">
        <StatCard icon="🧱" label="Elements Parsed" value={totalElements.toLocaleString()} color="blue" />
        <StatCard icon="🏗️" label="Element Types" value={uniqueTypes} color="purple" />
        <StatCard icon="🧪" label="Unique Materials" value={uniqueMaterials} color="yellow" />
        <StatCard icon="🏢" label="Building Storeys" value={totalStoreys} color="cyan" />
        <StatCard icon="📁" label="File Size" value={`${(data.fileSizeMb || 0).toFixed(1)} MB`} color="green" />
        <StatCard icon="✅" label="Data Quality" value="100%" color="orange" />
      </div>

      {/* Element Type Breakdown */}
      <div className="grid-2 mt-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">🧱 Element Type Distribution</span>
          </div>
          {topTypes.map(([type, count]) => {
            const pct = totalElements > 0 ? (count / totalElements) * 100 : 0;
            return (
              <div key={type} style={{ marginBottom: 10 }}>
                <div className="flex justify-between mb-1">
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {type.replace('Ifc', '')}
                  </span>
                  <span className="text-sm text-mono">{count} ({pct.toFixed(1)}%)</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">🧪 Materials</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {(data.materials || []).map(mat => (
              <span key={mat} className="badge badge-primary">{mat}</span>
            ))}
          </div>
          <div className="mt-2">
            <div className="card-header" style={{ marginBottom: 12 }}>
              <span className="card-title">🏢 Storeys</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {(data.storeys || []).map(s => (
                <span key={s} className="badge badge-warning">{s}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── StatCard Component ─────────────────────────────────────────────
function StatCard({ icon, label, value, color = 'blue' }) {
  return (
    <div className={`stat-card ${color} fade-in`}>
      <div className={`stat-icon ${color}`}>{icon}</div>
      <div className="stat-info">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
      </div>
    </div>
  );
}
