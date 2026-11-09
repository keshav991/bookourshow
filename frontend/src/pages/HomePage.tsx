import React from 'react';
import { Film, Ticket, ShieldCheck, Zap, ArrowRight, UserCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface HomePageProps {
  onNavigate: (view: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({ onNavigate }) => {
  const { user, profile } = useAuth();

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      {/* Hero Section */}
      <div className="relative rounded-3xl bg-gradient-to-b from-[#131b2e] to-[#0c1220] border border-[#22304d] p-8 sm:p-14 overflow-hidden shadow-2xl shadow-black/80">
        {/* Glow lights */}
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-rose-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-10 left-10 w-80 h-80 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-bold mb-6">
            <Film className="w-3.5 h-3.5" />
            <span>Next-Gen Cinema Ticketing Platform</span>
          </div>

          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.1]">
            Experience Cinema <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-rose-500 via-rose-400 to-amber-400">
              Without Waiting
            </span>
          </h1>

          <p className="mt-5 text-gray-300 text-base sm:text-lg leading-relaxed">
            Welcome to <strong>BookOurShow</strong>. Securely explore showtimes, reserve seats in real time, and enjoy your favorite movies at theatres near you.
          </p>

          <div className="mt-8 flex flex-wrap gap-4 items-center">
            {user ? (
              <button
                onClick={() => onNavigate('profile')}
                className="px-6 py-3.5 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white font-bold text-sm rounded-xl shadow-lg shadow-rose-950/60 transition-all flex items-center gap-2.5 group"
              >
                <UserCheck className="w-4 h-4" />
                <span>Go to Account Profile ({profile?.full_name || user.email?.split('@')[0]})</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            ) : (
              <>
                <button
                  onClick={() => onNavigate('register')}
                  className="px-6 py-3.5 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white font-bold text-sm rounded-xl shadow-lg shadow-rose-950/60 transition-all flex items-center gap-2.5 group hover:scale-105"
                >
                  <span>Create Account</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={() => onNavigate('login')}
                  className="px-6 py-3.5 bg-[#151f35] hover:bg-[#1b2845] text-gray-200 border border-[#2a3c63] font-bold text-sm rounded-xl transition-all"
                >
                  Sign In
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Feature Cards Grid */}
      <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-[#131b2e] rounded-2xl border border-[#22304d] p-6 shadow-lg hover:border-rose-500/30 transition-colors">
          <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 mb-4">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white mb-2">Supabase Auth Security</h3>
          <p className="text-xs text-gray-400 leading-relaxed">
            Enterprise-grade authentication with cryptographic JWT verification, password hashing, and automated PostgreSQL profile synchronization.
          </p>
        </div>

        <div className="bg-[#131b2e] rounded-2xl border border-[#22304d] p-6 shadow-lg hover:border-rose-500/30 transition-colors">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-4">
            <Zap className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white mb-2">FastAPI High Performance</h3>
          <p className="text-xs text-gray-400 leading-relaxed">
            Blazing fast asynchronous Python backend with SQLAlchemy 2.0 connection pooling and strictly isolated user data access.
          </p>
        </div>

        <div className="bg-[#131b2e] rounded-2xl border border-[#22304d] p-6 shadow-lg hover:border-rose-500/30 transition-colors">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-4">
            <Ticket className="w-6 h-6" />
          </div>
          <h3 className="text-base font-bold text-white mb-2">Instant Ticket Reservations</h3>
          <p className="text-xs text-gray-400 leading-relaxed">
            Ready for interactive screen seating, real-time lock management, and seamless booking operations.
          </p>
        </div>
      </div>
    </div>
  );
};
