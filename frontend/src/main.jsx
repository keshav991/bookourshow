import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/global.css';
import './styles/navbar.css';
import './styles/home.css';
import './styles/movie-card.css';
import './styles/movie-details.css';
import './styles/auth.css';
import './styles/shows.css';

class AppErrorBoundary extends React.Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('BookOurShow failed to render:', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ minHeight: '100vh', padding: '3rem', background: '#fff', color: '#111827', fontFamily: 'system-ui, sans-serif' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>BookOurShow could not load</h1>
          <p role="alert" style={{ marginTop: '1rem', color: '#b91c1c' }}>{this.state.error.message}</p>
          <p style={{ marginTop: '1rem', color: '#6b7280' }}>Open the browser console for details, then reload the page.</p>
        </main>
      );
    }
    return this.props.children;
  }
}

const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error('Could not find the #root element in index.html');
}

createRoot(rootElement).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>
);
