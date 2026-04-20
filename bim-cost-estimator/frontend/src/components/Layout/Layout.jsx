import React from 'react';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout({ children, projectId }) {
  return (
    <div className="app-layout">
      <Sidebar />
      <Header projectId={projectId} />
      <main className="main-content">
        <div className="page-container">
          {children}
        </div>
      </main>
    </div>
  );
}
