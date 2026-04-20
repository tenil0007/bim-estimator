import React, { useState } from 'react';
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import toast, { Toaster } from 'react-hot-toast';
import { predictTime } from '../services/api';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const chartColors = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#06b6d4', '#ef4444', '#f97316', '#ec4899'];

export default function TimeAnalysis({ projectData }) {
  const [timeData, setTimeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [modelType, setModelType] = useState('xgboost');

  const runPrediction = async () => {
    if (!projectData?.projectId) {
      toast.error('Load a project first');
      return;
    }
    setLoading(true);
    try {
      toast.loading('Running time prediction...', { id: 'time' });
      const result = await predictTime(projectData.projectId, modelType);
      setTimeData(result);
      toast.success(`Duration: ${(result.total_duration_days || 0).toFixed(1)} days`, { id: 'time' });
    } catch (err) {
      toast.error(err.message || 'Prediction failed', { id: 'time' });
    } finally {
      setLoading(false);
    }
  };

  if (!projectData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">⏱️</div>
        <h3 className="empty-state-title">No Project Loaded</h3>
        <p className="empty-state-text">Upload an IFC file on the Dashboard first.</p>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <Toaster position="top-right" toastOptions={{ style: { background: '#1a1f35', color: '#f1f5f9', border: '1px solid #1e293b', fontSize: '13px' } }} />

      <div className="section-header">
        <div>
          <h2 className="section-title">⏱️ Time Intelligence</h2>
          <p className="section-subtitle">Construction duration prediction by element</p>
        </div>
        <div className="btn-group">
          <select value={modelType} onChange={e => setModelType(e.target.value)} style={{ width: 180 }}>
            <option value="xgboost">XGBoost</option>
            <option value="random_forest">Random Forest</option>
            <option value="gradient_boosting">Gradient Boosting</option>
          </select>
          <button className="btn btn-primary" onClick={runPrediction} disabled={loading}>
            {loading ? '⏳ Predicting...' : '🚀 Predict Duration'}
          </button>
        </div>
      </div>

      {timeData ? (
        <div className="slide-up">
          <div className="stats-grid stagger">
            <div className="stat-card cyan">
              <div className="stat-icon cyan">⏱️</div>
              <div className="stat-info">
                <div className="stat-label">Total Labor Hours</div>
                <div className="stat-value">{(timeData.total_duration_hours || 0).toLocaleString()}</div>
              </div>
            </div>
            <div className="stat-card blue">
              <div className="stat-icon blue">📅</div>
              <div className="stat-info">
                <div className="stat-label">Calendar Days</div>
                <div className="stat-value">{(timeData.total_duration_days || 0).toFixed(1)}</div>
              </div>
            </div>
            <div className="stat-card green">
              <div className="stat-icon green">📊</div>
              <div className="stat-info">
                <div className="stat-label">Test R² Score</div>
                <div className="stat-value">{(timeData.metrics?.test_r2 || 0).toFixed(4)}</div>
              </div>
            </div>
            <div className="stat-card purple">
              <div className="stat-icon purple">🤖</div>
              <div className="stat-info">
                <div className="stat-label">Model</div>
                <div className="stat-value" style={{ fontSize: 16 }}>{timeData.model_used || modelType}</div>
              </div>
            </div>
          </div>

          <div className="grid-2 mt-2">
            <div className="card">
              <div className="card-header">
                <span className="card-title">🏗️ Duration by Element Type</span>
              </div>
              <div className="chart-container">
                <Bar data={{
                  labels: Object.keys(timeData.duration_breakdown || {}),
                  datasets: [{
                    label: 'Hours',
                    data: Object.values(timeData.duration_breakdown || {}),
                    backgroundColor: chartColors.map(c => c + '99'),
                    borderColor: chartColors,
                    borderWidth: 1,
                    borderRadius: 4,
                  }]
                }} options={{
                  plugins: { legend: { display: false } },
                  scales: {
                    x: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { display: false } },
                    y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                  },
                }} />
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">🏢 Duration by Storey</span>
              </div>
              <div className="chart-container">
                <Bar data={{
                  labels: Object.keys(timeData.storey_breakdown || {}),
                  datasets: [{
                    label: 'Hours',
                    data: Object.values(timeData.storey_breakdown || {}),
                    backgroundColor: '#06b6d499',
                    borderColor: '#06b6d4',
                    borderWidth: 1,
                    borderRadius: 4,
                  }]
                }} options={{
                  indexAxis: 'y',
                  plugins: { legend: { display: false } },
                  scales: {
                    x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.04)' } },
                    y: { ticks: { color: '#94a3b8', font: { size: 11 } }, grid: { display: false } },
                  },
                }} />
              </div>
            </div>
          </div>

          <div className="card mt-2">
            <div className="card-header">
              <span className="card-title">📋 Element Duration Predictions</span>
              <span className="badge badge-primary">{timeData.predictions?.length || 0} elements</span>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Element</th>
                    <th>Type</th>
                    <th>Material</th>
                    <th>Storey</th>
                    <th>Predicted Hours</th>
                  </tr>
                </thead>
                <tbody>
                  {(timeData.predictions || []).slice(0, 50).map((p, i) => (
                    <tr key={i}>
                      <td className="text-sm">{p.element_name || `Element ${i + 1}`}</td>
                      <td><span className="badge badge-primary">{p.ifc_type?.replace('Ifc', '')}</span></td>
                      <td className="text-sm">{p.material || 'N/A'}</td>
                      <td className="text-sm">{p.storey || 'N/A'}</td>
                      <td className="mono text-cyan">{(p.predicted_value || 0).toFixed(1)} hrs</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }}>⏱️</div>
          <h3 style={{ fontWeight: 700, marginBottom: 8 }}>Ready for Time Prediction</h3>
          <p className="text-muted">Click "Predict Duration" to estimate construction time.</p>
        </div>
      )}
    </div>
  );
}
