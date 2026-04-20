import React, { useState } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js';
import { Pie, Bar } from 'react-chartjs-2';
import toast, { Toaster } from 'react-hot-toast';
import { predictCost } from '../services/api';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

const chartColors = ['#3b82f6', '#8b5cf6', '#f59e0b', '#10b981', '#06b6d4', '#ef4444', '#f97316', '#ec4899', '#6366f1', '#14b8a6'];

export default function CostAnalysis({ projectData, setProjectData }) {
  const [costData, setCostData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [modelType, setModelType] = useState('xgboost');

  const runPrediction = async () => {
    if (!projectData?.projectId) {
      toast.error('Load a project from the Dashboard first');
      return;
    }
    setLoading(true);
    try {
      toast.loading('Running cost prediction...', { id: 'cost' });
      const result = await predictCost(projectData.projectId, modelType);
      setCostData(result);
      toast.success(`Cost prediction complete — ₹${(result.total_cost || 0).toLocaleString()}`, { id: 'cost' });
    } catch (err) {
      toast.error(err.message || 'Prediction failed', { id: 'cost' });
    } finally {
      setLoading(false);
    }
  };

  if (!projectData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">💰</div>
        <h3 className="empty-state-title">No Project Loaded</h3>
        <p className="empty-state-text">Upload an IFC file on the Dashboard to begin cost analysis.</p>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <Toaster position="top-right" toastOptions={{ style: { background: '#1a1f35', color: '#f1f5f9', border: '1px solid #1e293b', fontSize: '13px' } }} />

      <div className="section-header">
        <div>
          <h2 className="section-title">💰 Cost Intelligence</h2>
          <p className="section-subtitle">ML-driven construction cost estimation</p>
        </div>
        <div className="btn-group">
          <select value={modelType} onChange={e => setModelType(e.target.value)} style={{ width: 160 }}>
            <option value="xgboost">XGBoost</option>
            <option value="random_forest">Random Forest</option>
            <option value="lightgbm">LightGBM</option>
          </select>
          <button className="btn btn-primary" onClick={runPrediction} disabled={loading}>
            {loading ? '⏳ Predicting...' : '🚀 Predict Cost'}
          </button>
        </div>
      </div>

      {costData ? (
        <div className="slide-up">
          {/* Summary Stats */}
          <div className="stats-grid stagger">
            <div className="stat-card yellow">
              <div className="stat-icon yellow">💰</div>
              <div className="stat-info">
                <div className="stat-label">Total Estimated Cost</div>
                <div className="stat-value">₹{(costData.total_cost || 0).toLocaleString()}</div>
              </div>
            </div>
            <div className="stat-card blue">
              <div className="stat-icon blue">🤖</div>
              <div className="stat-info">
                <div className="stat-label">Model Used</div>
                <div className="stat-value" style={{ fontSize: 18 }}>{costData.model_used || modelType}</div>
              </div>
            </div>
            <div className="stat-card green">
              <div className="stat-icon green">📊</div>
              <div className="stat-info">
                <div className="stat-label">Test R² Score</div>
                <div className="stat-value">{(costData.metrics?.test_r2 || 0).toFixed(4)}</div>
              </div>
            </div>
            <div className="stat-card purple">
              <div className="stat-icon purple">📉</div>
              <div className="stat-info">
                <div className="stat-label">RMSE</div>
                <div className="stat-value">{(costData.metrics?.test_rmse || 0).toLocaleString()}</div>
              </div>
            </div>
          </div>

          {/* Charts */}
          <div className="grid-2 mt-2">
            <div className="card">
              <div className="card-header">
                <span className="card-title">🏗️ Cost by Element Type</span>
              </div>
              <div className="chart-container">
                <Pie data={{
                  labels: Object.keys(costData.cost_breakdown || {}),
                  datasets: [{
                    data: Object.values(costData.cost_breakdown || {}),
                    backgroundColor: chartColors,
                    borderWidth: 0,
                  }]
                }} options={{
                  plugins: {
                    legend: { position: 'bottom', labels: { color: '#94a3b8', font: { size: 11 } } },
                  },
                }} />
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <span className="card-title">🧪 Cost by Material</span>
              </div>
              <div className="chart-container">
                <Bar data={{
                  labels: Object.keys(costData.material_breakdown || {}),
                  datasets: [{
                    label: 'Cost (₹)',
                    data: Object.values(costData.material_breakdown || {}),
                    backgroundColor: chartColors.map(c => c + '99'),
                    borderColor: chartColors,
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

          {/* Element Table */}
          <div className="card mt-2">
            <div className="card-header">
              <span className="card-title">📋 Element Cost Predictions</span>
              <span className="badge badge-primary">{costData.predictions?.length || 0} elements</span>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Element</th>
                    <th>Type</th>
                    <th>Material</th>
                    <th>Storey</th>
                    <th>Predicted Cost</th>
                  </tr>
                </thead>
                <tbody>
                  {(costData.predictions || []).slice(0, 50).map((p, i) => (
                    <tr key={i}>
                      <td className="text-sm">{p.element_name || `Element ${i + 1}`}</td>
                      <td><span className="badge badge-primary">{p.ifc_type?.replace('Ifc', '')}</span></td>
                      <td className="text-sm">{p.material || 'N/A'}</td>
                      <td className="text-sm">{p.storey || 'N/A'}</td>
                      <td className="mono text-yellow">₹{(p.predicted_value || 0).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }}>💰</div>
          <h3 style={{ fontWeight: 700, marginBottom: 8 }}>Ready for Cost Prediction</h3>
          <p className="text-muted">Select a model type and click "Predict Cost" to analyze construction costs.</p>
        </div>
      )}
    </div>
  );
}
