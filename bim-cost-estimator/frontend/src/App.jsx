import React, { Suspense, lazy, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import { Loader } from './components/Common/Card';
import ErrorBoundary from './components/Common/ErrorBoundary';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const CostAnalysis = lazy(() => import('./pages/CostAnalysis'));
const TimeAnalysis = lazy(() => import('./pages/TimeAnalysis'));
const Schedule = lazy(() => import('./pages/Schedule'));
const Explainability = lazy(() => import('./pages/Explainability'));
const Reports = lazy(() => import('./pages/Reports'));

export default function App() {
  const [projectData, setProjectData] = useState(null);

  return (
    <Router>
      <ErrorBoundary>
        <Layout projectId={projectData?.projectId}>
          <Suspense fallback={<Loader text="Loading page..." />}>
            <Routes>
              <Route
                path="/"
                element={
                  <Dashboard
                    projectData={projectData}
                    setProjectData={setProjectData}
                    onProjectLoaded={(data) => setProjectData(data)}
                  />
                }
              />
              <Route
                path="/cost"
                element={<CostAnalysis projectData={projectData} setProjectData={setProjectData} />}
              />
              <Route path="/time" element={<TimeAnalysis projectData={projectData} />} />
              <Route path="/schedule" element={<Schedule projectData={projectData} />} />
              <Route path="/explainability" element={<Explainability projectData={projectData} />} />
              <Route path="/reports" element={<Reports projectData={projectData} />} />
            </Routes>
          </Suspense>
        </Layout>
      </ErrorBoundary>
    </Router>
  );
}
