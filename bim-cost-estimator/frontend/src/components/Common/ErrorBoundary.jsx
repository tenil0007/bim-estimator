import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    console.error('Application crashed:', error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'grid',
            placeItems: 'center',
            padding: '24px',
            background: 'var(--bg-primary)',
            color: 'var(--text-primary)',
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '720px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            <h2 style={{ marginBottom: '12px' }}>Something went wrong in the UI</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
              Refresh the page. If the problem continues, share the error shown below.
            </p>
            <pre
              style={{
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                color: 'var(--color-accent-red)',
                fontSize: '13px',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius-md)',
                padding: '12px',
              }}
            >
              {String(this.state.error?.message || this.state.error || 'Unknown error')}
            </pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
