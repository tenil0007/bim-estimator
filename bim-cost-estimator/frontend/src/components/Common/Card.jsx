import React from 'react';

export function Loader({ text = 'Loading...' }) {
  return (
    <div className="loader">
      <div className="spinner" />
      <span className="loader-text">{text}</span>
    </div>
  );
}

export function Card({ title, subtitle, children, actions, className = '' }) {
  return (
    <div className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <span className="card-title">{title}</span>}
            {subtitle && <div className="card-subtitle">{subtitle}</div>}
          </div>
          {actions && <div>{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export function StatCard({ icon, label, value, color = 'blue', change }) {
  return (
    <div className={`stat-card ${color} fade-in`}>
      <div className={`stat-icon ${color}`}>{icon}</div>
      <div className="stat-info">
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
        {change && (
          <div className={`stat-change ${change >= 0 ? 'positive' : 'negative'}`}>
            {change >= 0 ? '↑' : '↓'} {Math.abs(change)}%
          </div>
        )}
      </div>
    </div>
  );
}

export function EmptyState({ icon = '📭', title, text, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-text">{text}</p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
