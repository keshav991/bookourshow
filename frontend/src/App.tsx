import React, { useState } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ProfilePage } from './pages/ProfilePage';
import { LoadingSpinner } from './components/LoadingSpinner';

const MainContent: React.FC = () => {
  const { user, loading } = useAuth();
  const [currentView, setCurrentView] = useState<string>('home');

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0b0f19] flex flex-col items-center justify-center text-white">
        <LoadingSpinner size="lg" className="text-rose-500 mb-4" />
        <p className="text-xs font-semibold text-gray-400 tracking-wider uppercase">
          Initializing Session...
        </p>
      </div>
    );
  }

  // View routing handler
  const renderView = () => {
    switch (currentView) {
      case 'login':
        return user ? (
          <ProfilePage onNavigate={setCurrentView} />
        ) : (
          <LoginPage onNavigate={setCurrentView} />
        );

      case 'register':
        return user ? (
          <ProfilePage onNavigate={setCurrentView} />
        ) : (
          <RegisterPage onNavigate={setCurrentView} />
        );

      case 'profile':
        return user ? (
          <ProfilePage onNavigate={setCurrentView} />
        ) : (
          <LoginPage onNavigate={setCurrentView} />
        );

      case 'home':
      default:
        return <HomePage onNavigate={setCurrentView} />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f19]">
      <Navbar currentView={currentView} onNavigate={setCurrentView} />
      <main className="flex-1">{renderView()}</main>

      {/* Footer */}
      <footer className="border-t border-[#1b253b] bg-[#0d1322] py-8 text-center text-xs text-gray-400">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 font-bold text-gray-300">
            <span>BookOurShow</span>
            <span className="text-gray-400">•</span>
            <span className="text-gray-400 font-normal">FastAPI + Supabase Auth</span>
          </div>
          <div className="text-gray-400">
            Secure Movie Ticket Reservation Platform
          </div>
        </div>
      </footer>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainContent />
    </AuthProvider>
  );
};

export default App;
