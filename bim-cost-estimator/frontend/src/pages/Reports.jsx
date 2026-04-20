import React, { useState } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { generateReport, exportData } from '../services/api';

export default function Reports({ projectData }) {
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState({
    includeCost: true,
    includeTime: true,
    includeSchedule: true,
    includeShap: true,
    title: 'BIM Cost & Time Estimation Report',
    company: 'Larsen & Toubro Limited',
  });

  const downloadReport = async () => {
    if (!projectData?.projectId) {
      toast.error('Load a project first');
      return;
    }
    setLoading(true);
    try {
      toast.loading('Generating PDF report...', { id: 'report' });
      await generateReport(projectData.projectId, options);
      toast.success('Report downloaded!', { id: 'report' });
    } catch (err) {
      toast.error(err.message || 'Report generation failed', { id: 'report' });
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format) => {
    if (!projectData?.projectId) {
      toast.error('Load a project first');
      return;
    }
    try {
      toast.loading(`Exporting ${format.toUpperCase()}...`, { id: 'export' });
      await exportData(projectData.projectId, format);
      toast.success(`${format.toUpperCase()} exported!`, { id: 'export' });
    } catch (err) {
      toast.error(err.message || 'Export failed', { id: 'export' });
    }
  };

  if (!projectData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📄</div>
        <h3 className="empty-state-title">No Project Loaded</h3>
        <p className="empty-state-text">Upload an IFC file and run predictions first.</p>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <Toaster position="top-right" toastOptions={{ style: { background: '#1a1f35', color: '#f1f5f9', border: '1px solid #1e293b', fontSize: '13px' } }} />

      <div className="section-header">
        <div>
          <h2 className="section-title">📄 Report Generation</h2>
          <p className="section-subtitle">Generate comprehensive AI project reports</p>
        </div>
      </div>

      <div className="grid-2">
        {/* Report Configuration */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">⚙️ Report Configuration</span>
          </div>

          <div style={{ display: 'grid', gap: 16 }}>
            <div>
              <label className="text-sm text-muted" style={{ display: 'block', marginBottom: 6 }}>Report Title</label>
              <input
                type="text"
                value={options.title}
                onChange={e => setOptions({ ...options, title: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm text-muted" style={{ display: 'block', marginBottom: 6 }}>Company Name</label>
              <input
                type="text"
                value={options.company}
                onChange={e => setOptions({ ...options, company: e.target.value })}
              />
            </div>

            <div style={{ display: 'grid', gap: 10 }}>
              <label className="text-sm text-muted">Include Sections</label>
              {[
                { key: 'includeCost', label: '💰 Cost Analysis', icon: '💰' },
                { key: 'includeTime', label: '⏱️ Time Estimation', icon: '⏱️' },
                { key: 'includeSchedule', label: '📅 Construction Schedule', icon: '📅' },
                { key: 'includeShap', label: '🧠 AI Explainability', icon: '🧠' },
              ].map(item => (
                <label
                  key={item.key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '10px 14px',
                    background: options[item.key] ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-surface)',
                    borderRadius: 'var(--radius-sm)',
                    border: `1px solid ${options[item.key] ? 'var(--border-accent)' : 'var(--border-primary)'}`,
                    cursor: 'pointer',
                    transition: 'var(--transition-fast)',
                    fontSize: 13,
                  }}
                >
                  <input
                    type="checkbox"
                    checked={options[item.key]}
                    onChange={e => setOptions({ ...options, [item.key]: e.target.checked })}
                    style={{ accentColor: 'var(--accent-blue)' }}
                  />
                  {item.label}
                </label>
              ))}
            </div>

            <button className="btn btn-warning btn-lg" onClick={downloadReport} disabled={loading} style={{ width: '100%', marginTop: 8 }}>
              {loading ? '⏳ Generating...' : '📥 Generate & Download PDF Report'}
            </button>
          </div>
        </div>

        {/* Data Export & Summary */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">📊 Project Summary</span>
            </div>
            <div>
              <div className="metric-row">
                <span className="metric-label">Project ID</span>
                <span className="metric-value text-mono text-sm">{projectData.projectId?.slice(0, 12)}...</span>
              </div>
              <div className="metric-row">
                <span className="metric-label">File</span>
                <span className="metric-value text-sm">{projectData.filename}</span>
              </div>
              <div className="metric-row">
                <span className="metric-label">Elements</span>
                <span className="metric-value">{projectData.totalElements?.toLocaleString()}</span>
              </div>
              <div className="metric-row">
                <span className="metric-label">Materials</span>
                <span className="metric-value">{projectData.materials?.length || 0}</span>
              </div>
              <div className="metric-row">
                <span className="metric-label">Storeys</span>
                <span className="metric-value">{projectData.storeys?.length || 0}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">💾 Data Export</span>
            </div>
            <p className="text-sm text-muted mb-2">
              Export extracted BIM element data for external analysis.
            </p>
            <div className="btn-group">
              <button className="btn btn-secondary" onClick={() => handleExport('csv')}>
                📊 Export CSV
              </button>
              <button className="btn btn-secondary" onClick={() => handleExport('parquet')}>
                🗃️ Export Parquet
              </button>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">📝 Report Contents</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.8 }}>
              The generated PDF report includes:
              <ul style={{ paddingLeft: 16, marginTop: 8 }}>
                <li>Executive summary with project overview</li>
                <li>Cost breakdown by element type & material</li>
                <li>Duration estimates with phase analysis</li>
                <li>CPM schedule with critical path</li>
                <li>SHAP feature importance charts</li>
                <li>Model performance metrics (R², RMSE, MAE)</li>
                <li>Data quality assessment</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
