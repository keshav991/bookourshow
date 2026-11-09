import React, { useState } from 'react';
import { Mail, Lock, Eye, EyeOff, Film, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/LoadingSpinner';

interface LoginPageProps {
  onNavigate: (view: string) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onNavigate }) => {
  const { signIn, error: authError, clearError } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    clearError();

    // Client-side form validation
    if (!email.trim()) {
      setFormError('Email address is required.');
      return;
    }
    if (!password) {
      setFormError('Password is required.');
      return;
    }

    try {
      setLoading(true);
      await signIn(email.trim(), password);
      onNavigate('profile');
    } catch (err: any) {
      // Supabase Auth error message
      setFormError(err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md bg-[#131b2e] rounded-3xl border border-[#22304d] p-6 sm:p-8 shadow-2xl shadow-black/60 relative overflow-hidden">
        {/* Cinema ambient glow */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Card Header */}
        <div className="text-center mb-8 relative">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-rose-600 to-amber-500 text-white shadow-xl shadow-rose-950 mb-4">
            <Film className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Welcome Back</h1>
          <p className="text-sm text-gray-400 mt-1">Sign in to book tickets and manage your movie reservations</p>
        </div>

        {/* Alerts */}
        {(formError || authError) && (
          <div className="mb-6">
            <Alert
              type="error"
              message={formError || authError || 'Authentication failed'}
              onClose={() => {
                setFormError(null);
                clearError();
              }}
            />
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Email input */}
          <div>
            <label className="block text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">
              Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full pl-10 pr-4 py-3 bg-[#0d1424] border border-[#22304d] focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 rounded-xl text-sm text-white placeholder-gray-500 transition-all outline-none"
                disabled={loading}
                autoComplete="email"
              />
            </div>
          </div>

          {/* Password input */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-gray-300 uppercase tracking-wider">
                Password
              </label>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-10 pr-11 py-3 bg-[#0d1424] border border-[#22304d] focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 rounded-xl text-sm text-white placeholder-gray-500 transition-all outline-none"
                disabled={loading}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-400 hover:text-gray-200 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 px-4 bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white font-bold text-sm rounded-xl shadow-lg shadow-rose-950/50 hover:shadow-rose-900/80 transition-all flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {loading ? (
              <>
                <LoadingSpinner size="sm" className="text-white" />
                <span>Authenticating with Supabase...</span>
              </>
            ) : (
              <>
                <span>Sign In</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </form>

        {/* Footer switcher */}
        <div className="mt-8 text-center text-xs text-gray-400 border-t border-[#1e2a44] pt-6">
          Don't have an account?{' '}
          <button
            onClick={() => onNavigate('register')}
            className="text-rose-400 hover:text-rose-300 font-bold transition-colors underline-offset-4 hover:underline"
          >
            Create one now
          </button>
        </div>
      </div>
    </div>
  );
};
