import React from 'react';
import { useLocation } from 'react-router-dom';

const pageTitles = {
  '/': 'Dashboard Overview',
  '/cost': 'Cost Analysis',
  '/time': 'Time Estimation',
  '/schedule': 'Project Schedule',
  '/explainability': 'AI Explainability',
  '/reports': 'Report Generation',
};

export default function Header({ projectId }) {
  const location = useLocation();
  const title = pageTitles[location.pathname] || 'BIM Estimator';

  return (
    <header className="header" id="header">
      <h1 className="header-title">{title}</h1>
      <div className="header-actions">
        {projectId && (
          <span className="badge badge-primary">
            Project: {projectId}
          </span>
        )}
        <span className="badge badge-success">
          v1.0.0
        </span>
      </div>
    </header>
  );
}
