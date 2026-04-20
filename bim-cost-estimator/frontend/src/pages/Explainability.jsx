import React, { useState } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { getShapExplanation } from '../services/api';

export default function Explainability({ projectData }) {
  const [shapData, setShapData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [model, setModel] = useState('cost');

  const loadExplanation = async () => {
    if (!projectData?.projectId) {
      toast.error('Load a project first');
      return;
    }
    setLoading(true);
    try {
      toast.loading('Computing SHAP explanations...', { id: 'shap' });
      const result = await getShapExplanation(projectData.projectId, model);
      setShapData(result);
      toast.success('SHAP explanations ready', { id: 'shap' });
    } catch (err) {
      toast.error(err.message || 'SHAP analysis failed', { id: 'shap' });
    } finally {
      setLoading(false);
    }
  };

  if (!projectData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">🧠</div>
        <h3 className="empty-state-title">No Project Loaded</h3>
        <p className="empty-state-text">Upload an IFC file and run predictions first.</p>
      </div>
    );
  }

  const globalExp = shapData?.global_explanation || {};
  const localExp = shapData?.local_explanation || {};
  const plotData = globalExp?.plot_data || {};
  const waterfallData = localExp?.waterfall_data || {};

  return (
    <div className="fade-in">
      <Toaster position="top-right" toastOptions={{ style: { background: '#1a1f35', color: '#f1f5f9', border: '1px solid #1e293b', fontSize: '13px' } }} />

      <div className="section-header">
        <div>
          <h2 className="section-title">🧠 AI Explainability</h2>
          <p className="section-subtitle">SHAP-based feature importance and prediction breakdown</p>
        </div>
        <div className="btn-group">
          <select value={model} onChange={e => setModel(e.target.value)} style={{ width: 140 }}>
            <option value="cost">Cost Model</option>
            <option value="time">Time Model</option>
          </select>
          <button className="btn btn-primary" onClick={loadExplanation} disabled={loading}>
            {loading ? '⏳ Computing...' : '🧠 Explain Model'}
          </button>
        </div>
      </div>

      {shapData ? (
        <div className="slide-up">
          <div className="grid-2">
            {/* Global Feature Importance */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">📊 {plotData.title || 'Feature Importance'}</span>
              </div>
              <div>
                {(plotData.labels || []).map((label, i) => {
                  const value = plotData.values?.[i] || 0;
                  const maxVal = Math.max(...(plotData.values || [1]));
                  const pct = maxVal > 0 ? (value / maxVal) * 100 : 0;
                  const direction = globalExp?.feature_direction?.[label];
                  return (
                    <div key={label} className="shap-bar">
                      <span className="shap-feature-name">{label}</span>
                      <div className="shap-bar-track">
                        <div
                          className={`shap-bar-fill ${direction === 'increases' ? 'positive' : 'negative'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="shap-value">{value.toFixed(3)}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Local Explanation (Waterfall) */}
            <div className="card">
              <div className="card-header">
                <span className="card-title">🔍 {waterfallData.title || 'Element Breakdown'}</span>
              </div>
              {localExp.base_value !== undefined && (
                <div className="metric-row">
                  <span className="metric-label">Base Value</span>
                  <span className="metric-value text-blue">{localExp.base_value?.toFixed(2)}</span>
                </div>
              )}
              {localExp.predicted_value !== undefined && (
                <div className="metric-row">
                  <span className="metric-label">Predicted Value</span>
                  <span className="metric-value text-yellow">{localExp.predicted_value?.toFixed(2)}</span>
                </div>
              )}
              <div className="mt-2">
                {(waterfallData.features || []).map((feat, i) => {
                  const val = waterfallData.values?.[i] || 0;
                  const isPositive = val >= 0;
                  return (
                    <div key={feat} className="shap-bar">
                      <span className="shap-feature-name">{feat}</span>
                      <div className="shap-bar-track" style={{ display: 'flex', justifyContent: isPositive ? 'flex-start' : 'flex-end' }}>
                        <div
                          className={`shap-bar-fill ${isPositive ? 'positive' : 'negative'}`}
                          style={{ width: `${Math.min(Math.abs(val) * 20, 100)}%` }}
                        />
                      </div>
                      <span className="shap-value" style={{ color: isPositive ? 'var(--accent-red)' : 'var(--accent-blue)' }}>
                        {val >= 0 ? '+' : ''}{val.toFixed(4)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* AI Recommendations */}
          <div className="card mt-2">
            <div className="card-header">
              <span className="card-title">💡 AI Recommendations</span>
            </div>
            <div style={{ display: 'grid', gap: 12 }}>
              {(plotData.labels || []).slice(0, 3).map((feature, i) => {
                const direction = globalExp?.feature_direction?.[feature];
                return (
                  <div key={i} style={{
                    padding: '12px 16px',
                    background: 'var(--bg-surface)',
                    borderRadius: 'var(--radius-sm)',
                    borderLeft: `3px solid ${direction === 'increases' ? 'var(--accent-yellow)' : 'var(--accent-blue)'}`,
                  }}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                      {feature.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </div>
                    <div className="text-sm text-muted">
                      This feature {direction === 'increases' ? '↑ increases' : '↓ decreases'} the predicted {model} value.
                      {i === 0 && ' This is the strongest driver — optimizing this will have the highest impact.'}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }}>🧠</div>
          <h3 style={{ fontWeight: 700, marginBottom: 8 }}>Ready for Explainability</h3>
          <p className="text-muted">Run predictions first, then click "Explain Model" to see SHAP analysis.</p>
        </div>
      )}
    </div>
  );
}
