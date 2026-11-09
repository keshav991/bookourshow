import React, { useEffect, useState } from 'react';
import { Film, LogOut, Ticket, CheckCircle2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';

interface NavbarProps {
  currentView: string;
  onNavigate: (view: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const { user, profile, signOut } = useAuth();
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    api.checkHealth()
      .then(() => setBackendHealthy(true))
      .catch(() => setBackendHealthy(false));
  }, []);

  return (
    <header className="sticky top-0 z-50 bg-[#0b0f19]/90 backdrop-blur-xl border-b border-[#1f293d]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <div
          onClick={() => onNavigate('home')}
          className="flex items-center gap-3 cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-700 to-rose-500 flex items-center justify-center shadow-lg shadow-rose-900/40 group-hover:scale-105 transition-transform duration-200">
            <Film className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-xl font-bold tracking-tight text-white group-hover:text-rose-400 transition-colors">
              BookOur<span className="text-rose-500">Show</span>
            </span>
            <div className="flex items-center gap-1.5 text-[10px] text-gray-400">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-rose-500"></span>
              Cinema Tickets
            </div>
          </div>
        </div>

        {/* Center Navigation */}
        <nav className="hidden md:flex items-center gap-1 bg-[#131b2e] px-3 py-1.5 rounded-full border border-[#22304d]">
          <button
            onClick={() => onNavigate('home')}
            className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
              currentView === 'home'
                ? 'bg-rose-600 text-white shadow-md shadow-rose-900/50'
                : 'text-gray-300 hover:text-white hover:bg-[#1a253f]'
            }`}
          >
            Home
          </button>
          <button
            onClick={() => onNavigate('home')}
            className="px-4 py-1.5 rounded-full text-xs font-semibold text-gray-400 hover:text-gray-200 transition-all flex items-center gap-1.5 cursor-not-allowed opacity-75"
            title="Cinema bookings coming soon"
          >
            <Ticket className="w-3.5 h-3.5" />
            <span>Movies</span>
            <span className="text-[9px] bg-rose-500/20 text-rose-300 px-1.5 py-0.5 rounded-full font-bold uppercase">Soon</span>
          </button>
          {user && (
            <button
              onClick={() => onNavigate('profile')}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all ${
                currentView === 'profile'
                  ? 'bg-rose-600 text-white shadow-md shadow-rose-900/50'
                  : 'text-gray-300 hover:text-white hover:bg-[#1a253f]'
              }`}
            >
              My Profile
            </button>
          )}
        </nav>

        {/* Right Action Area */}
        <div className="flex items-center gap-3">
          {/* Backend Status indicator */}
          <div
            className="hidden sm:flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-[#131b2e] border border-[#22304d]"
            title={backendHealthy ? "FastAPI backend connected" : "Connecting to FastAPI..."}
          >
            {backendHealthy ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-gray-300 font-medium text-[11px]">API Online</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3.5 h-3.5 text-amber-400 animate-pulse" />
                <span className="text-gray-400 text-[11px]">API Offline</span>
              </>
            )}
          </div>

          {user ? (
            <div className="flex items-center gap-2 sm:gap-3">
              <button
                onClick={() => onNavigate('profile')}
                className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-[#162035] hover:bg-[#1c2a47] border border-[#28385a] transition-colors text-left"
              >
                <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-rose-500 to-amber-500 flex items-center justify-center font-bold text-white text-xs shadow">
                  {(profile?.full_name || user.email || 'U').charAt(0).toUpperCase()}
                </div>
                <div className="hidden sm:block">
                  <div className="text-xs font-semibold text-white truncate max-w-[120px]">
                    {profile?.full_name || user.email?.split('@')[0]}
                  </div>
                  <div className="text-[10px] uppercase font-bold text-rose-400 tracking-wider">
                    {profile?.role || 'customer'}
                  </div>
                </div>
              </button>

              <button
                onClick={() => signOut()}
                className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-rose-950/60 hover:border-rose-800/80 border border-transparent transition-all"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <button
                onClick={() => onNavigate('login')}
                className="px-3.5 py-1.5 text-xs font-semibold text-gray-300 hover:text-white transition-colors"
              >
                Sign In
              </button>
              <button
                onClick={() => onNavigate('register')}
                className="px-4 py-2 text-xs font-bold text-white bg-rose-600 hover:bg-rose-500 rounded-xl shadow-lg shadow-rose-900/30 transition-all hover:scale-105"
              >
                Get Started
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
