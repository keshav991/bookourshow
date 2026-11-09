import React, { useState } from 'react';
import { Mail, Lock, User, Eye, EyeOff, Film, ArrowRight, CheckCircle2, Inbox } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/LoadingSpinner';

interface RegisterPageProps {
  onNavigate: (view: string) => void;
}

export const RegisterPage: React.FC<RegisterPageProps> = ({ onNavigate }) => {
  const { signUp, error: authError, clearError } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [verificationRequired, setVerificationRequired] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    clearError();

    // Form validations
    if (!fullName.trim()) {
      setFormError('Please enter your full name.');
      return;
    }
    if (!email.trim() || !email.includes('@')) {
      setFormError('Please enter a valid email address.');
      return;
    }
    if (password.length < 6) {
      setFormError('Password must be at least 6 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setFormError('Passwords do not match.');
      return;
    }

    try {
      setLoading(true);
      const { needsEmailVerification } = await signUp(email.trim(), password, fullName.trim());

      if (needsEmailVerification) {
        setRegisteredEmail(email.trim());
        setVerificationRequired(true);
      } else {
        // Instant login session established
        onNavigate('profile');
      }
    } catch (err: any) {
      setFormError(err.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // State: Email verification prompt screen
  if (verificationRequired) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8">
        <div className="w-full max-w-md bg-[#131b2e] rounded-3xl border border-[#22304d] p-8 shadow-2xl shadow-black/60 text-center relative overflow-hidden">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto mb-6 shadow-lg shadow-emerald-950">
            <Inbox className="w-8 h-8" />
          </div>

          <h2 className="text-2xl font-bold text-white mb-2">Check Your Email</h2>
          <p className="text-sm text-gray-300 leading-relaxed mb-4">
            We sent a verification link to <br />
            <strong className="text-rose-400 font-semibold">{registeredEmail}</strong>
          </p>

          <div className="bg-[#0e1626] rounded-2xl p-4 border border-[#22304d] text-left text-xs text-gray-400 space-y-2 mb-6">
            <div className="flex items-center gap-2 text-emerald-300 font-semibold">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>PostgreSQL profile initialized</span>
            </div>
            <p>
              Once you click the link in your email, your account will be activated and you can sign in to book movie tickets.
            </p>
          </div>

          <button
            onClick={() => onNavigate('login')}
            className="w-full py-3.5 px-4 bg-rose-600 hover:bg-rose-500 text-white font-bold text-sm rounded-xl transition-all shadow-lg shadow-rose-950/40"
          >
            Go to Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="w-full max-w-md bg-[#131b2e] rounded-3xl border border-[#22304d] p-6 sm:p-8 shadow-2xl shadow-black/60 relative overflow-hidden">
        {/* Glow ambient */}
        <div className="absolute -top-24 -left-24 w-48 h-48 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="text-center mb-8 relative">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-rose-600 to-amber-500 text-white shadow-xl shadow-rose-950 mb-4">
            <Film className="w-7 h-7" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">Create Account</h1>
          <p className="text-sm text-gray-400 mt-1">Join BookOurShow to experience seamless movie booking</p>
        </div>

        {(formError || authError) && (
          <div className="mb-6">
            <Alert
              type="error"
              message={formError || authError || 'Registration failed'}
              onClose={() => {
                setFormError(null);
                clearError();
              }}
            />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Full Name */}
          <div>
            <label className="block text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">
              Full Name
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                <User className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Keshav Sharma"
                className="w-full pl-10 pr-4 py-3 bg-[#0d1424] border border-[#22304d] focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 rounded-xl text-sm text-white placeholder-gray-500 transition-all outline-none"
                disabled={loading}
              />
            </div>
          </div>

          {/* Email */}
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

          {/* Password */}
          <div>
            <label className="block text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">
              Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 6 characters"
                className="w-full pl-10 pr-11 py-3 bg-[#0d1424] border border-[#22304d] focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 rounded-xl text-sm text-white placeholder-gray-500 transition-all outline-none"
                disabled={loading}
                autoComplete="new-password"
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

          {/* Confirm Password */}
          <div>
            <label className="block text-xs font-bold text-gray-300 uppercase tracking-wider mb-2">
              Confirm Password
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password"
                className="w-full pl-10 pr-4 py-3 bg-[#0d1424] border border-[#22304d] focus:border-rose-500 focus:ring-2 focus:ring-rose-500/20 rounded-xl text-sm text-white placeholder-gray-500 transition-all outline-none"
                disabled={loading}
                autoComplete="new-password"
              />
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
                <span>Registering in Supabase...</span>
              </>
            ) : (
              <>
                <span>Create My Account</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 text-center text-xs text-gray-400 border-t border-[#1e2a44] pt-6">
          Already have an account?{' '}
          <button
            onClick={() => onNavigate('login')}
            className="text-rose-400 hover:text-rose-300 font-bold transition-colors underline-offset-4 hover:underline"
          >
            Sign in here
          </button>
        </div>
      </div>
    </div>
  );
};
