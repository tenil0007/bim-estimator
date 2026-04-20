import React, { useState } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { generateSchedule } from '../services/api';

export default function Schedule({ projectData }) {
  const [scheduleData, setScheduleData] = useState(null);
  const [loading, setLoading] = useState(false);

  const runSchedule = async () => {
    if (!projectData?.projectId) {
      toast.error('Load a project first');
      return;
    }
    setLoading(true);
    try {
      toast.loading('Generating CPM schedule...', { id: 'schedule' });
      const result = await generateSchedule(projectData.projectId);
      setScheduleData(result);
      toast.success(`Schedule complete — ${result.total_duration_days?.toFixed(0)} days`, { id: 'schedule' });
    } catch (err) {
      toast.error(err.message || 'Scheduling failed', { id: 'schedule' });
    } finally {
      setLoading(false);
    }
  };

  if (!projectData) {
    return (
      <div className="empty-state">
        <div className="empty-state-icon">📅</div>
        <h3 className="empty-state-title">No Project Loaded</h3>
        <p className="empty-state-text">Upload an IFC file on the Dashboard first.</p>
      </div>
    );
  }

  const gantt = scheduleData?.gantt_data || [];
  const maxDay = scheduleData?.total_duration_days || 1;
  const criticalPath = scheduleData?.critical_path || [];

  return (
    <div className="fade-in">
      <Toaster position="top-right" toastOptions={{ style: { background: '#1a1f35', color: '#f1f5f9', border: '1px solid #1e293b', fontSize: '13px' } }} />

      <div className="section-header">
        <div>
          <h2 className="section-title">📅 Construction Schedule</h2>
          <p className="section-subtitle">CPM-based scheduling with critical path analysis</p>
        </div>
        <button className="btn btn-primary" onClick={runSchedule} disabled={loading}>
          {loading ? '⏳ Generating...' : '🚀 Generate Schedule'}
        </button>
      </div>

      {scheduleData ? (
        <div className="slide-up">
          {/* Summary */}
          <div className="stats-grid stagger">
            <div className="stat-card blue">
              <div className="stat-icon blue">📅</div>
              <div className="stat-info">
                <div className="stat-label">Total Duration</div>
                <div className="stat-value">{maxDay.toFixed(0)} days</div>
              </div>
            </div>
            <div className="stat-card orange">
              <div className="stat-icon orange">🔴</div>
              <div className="stat-info">
                <div className="stat-label">Critical Activities</div>
                <div className="stat-value">{scheduleData.summary?.critical_activities || 0}</div>
              </div>
            </div>
            <div className="stat-card green">
              <div className="stat-icon green">📊</div>
              <div className="stat-info">
                <div className="stat-label">Total Activities</div>
                <div className="stat-value">{scheduleData.summary?.total_activities || 0}</div>
              </div>
            </div>
            <div className="stat-card purple">
              <div className="stat-icon purple">⏳</div>
              <div className="stat-info">
                <div className="stat-label">Avg Float</div>
                <div className="stat-value">{(scheduleData.summary?.avg_float_days || 0).toFixed(1)} d</div>
              </div>
            </div>
          </div>

          {/* Critical Path */}
          <div className="card mt-2">
            <div className="card-header">
              <span className="card-title">🔴 Critical Path</span>
              <span className="badge badge-danger">{criticalPath.length} activities</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {criticalPath.map((name, i) => (
                <span key={i} className="badge badge-danger">
                  {i > 0 && '→ '}{name}
                </span>
              ))}
            </div>
          </div>

          {/* Gantt Chart */}
          <div className="card mt-2">
            <div className="card-header">
              <span className="card-title">📊 Gantt Chart</span>
            </div>
            <div className="gantt-container">
              {gantt.map((item, i) => {
                const leftPct = (item.start_day / maxDay) * 100;
                const widthPct = Math.max(1, (item.duration / maxDay) * 100);
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
                    <div style={{ width: 200, fontSize: 11, color: 'var(--text-secondary)', textAlign: 'right', flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {item.name}
                    </div>
                    <div style={{ flex: 1, position: 'relative', height: 28 }}>
                      <div
                        className={`gantt-bar ${item.is_critical ? 'critical' : 'normal'}`}
                        style={{ position: 'absolute', left: `${leftPct}%`, width: `${widthPct}%` }}
                        title={`${item.name}: Day ${item.start_day?.toFixed(0)} → ${item.end_day?.toFixed(0)} (${item.duration?.toFixed(1)}d) | Float: ${item.total_float?.toFixed(1)}d`}
                      >
                        <span style={{ fontSize: 10, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.duration?.toFixed(0)}d
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Schedule Table */}
          <div className="card mt-2">
            <div className="card-header">
              <span className="card-title">📋 Schedule Details</span>
            </div>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Activity</th>
                    <th>ES</th>
                    <th>EF</th>
                    <th>LS</th>
                    <th>LF</th>
                    <th>Duration</th>
                    <th>Float</th>
                    <th>Critical</th>
                  </tr>
                </thead>
                <tbody>
                  {gantt.map((item, i) => (
                    <tr key={i}>
                      <td className="text-sm" style={{ fontWeight: item.is_critical ? 600 : 400 }}>
                        {item.name}
                      </td>
                      <td className="mono">{item.early_start?.toFixed(1)}</td>
                      <td className="mono">{item.early_finish?.toFixed(1)}</td>
                      <td className="mono">{item.late_start?.toFixed(1)}</td>
                      <td className="mono">{item.late_finish?.toFixed(1)}</td>
                      <td className="mono">{item.duration?.toFixed(1)}d</td>
                      <td className="mono">{item.total_float?.toFixed(1)}d</td>
                      <td>{item.is_critical ? <span className="badge badge-danger">Yes</span> : <span className="text-muted text-xs">No</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }}>📅</div>
          <h3 style={{ fontWeight: 700, marginBottom: 8 }}>Ready for Scheduling</h3>
          <p className="text-muted">Click "Generate Schedule" to create the CPM construction schedule.</p>
        </div>
      )}
    </div>
  );
}
