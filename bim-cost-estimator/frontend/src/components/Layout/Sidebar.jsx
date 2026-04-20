import React from 'react';
import { NavLink } from 'react-router-dom';

const navItems = [
  { label: 'Analytics', section: true },
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/cost', label: 'Cost Analysis', icon: '💰' },
  { path: '/time', label: 'Time Estimation', icon: '⏱️' },
  { path: '/schedule', label: 'Schedule / Gantt', icon: '📅' },
  { label: 'Intelligence', section: true },
  { path: '/explainability', label: 'AI Explainability', icon: '🧠' },
  { label: 'Output', section: true },
  { path: '/reports', label: 'Reports', icon: '📄' },
];

export default function Sidebar() {
  return (
    <aside className="sidebar" id="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">BIM</div>
        <div className="sidebar-brand-text">
          <h2>BIM Estimator</h2>
          <span>L&T Construction</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navItems.map((item, idx) => {
          if (item.section) {
            return (
              <div className="sidebar-section-label" key={idx}>
                {item.label}
              </div>
            );
          }
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              end={item.path === '/'}
            >
              <span style={{ fontSize: '16px' }}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-footer-badge">
          <span className="status-dot active"></span>
          <span>System Online</span>
        </div>
      </div>
    </aside>
  );
}
