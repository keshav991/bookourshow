import React, { useState } from 'react';
import { User, Shield, Key, RefreshCw, Save, LogOut, CheckCircle2, Ticket, Terminal } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { Alert } from '../components/Alert';
import { LoadingSpinner } from '../components/LoadingSpinner';

interface ProfilePageProps {
  onNavigate: (view: string) => void;
}

export const ProfilePage: React.FC<ProfilePageProps> = ({ onNavigate }) => {
  const { user, profile, profileLoading, refreshProfile, signOut } = useAuth();
  const [editingName, setEditingName] = useState(false);
  const [fullNameInput, setFullNameInput] = useState(profile?.full_name || '');
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Live FastAPI API inspection state
  const [testingEndpoint, setTestingEndpoint] = useState<string | null>(null);
  const [apiResponse, setApiResponse] = useState<{ endpoint: string; status: number; data: any } | null>(null);

  // Synchronize input when profile loads
  React.useEffect(() => {
    if (profile?.full_name) {
      setFullNameInput(profile.full_name);
    }
  }, [profile]);

  const handleUpdateName = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullNameInput.trim()) return;

    try {
      setSaving(true);
      setActionError(null);
      await api.updateUserProfile(fullNameInput.trim());
      await refreshProfile();
      setEditingName(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setActionError(err.message || 'Failed to update full name.');
    } finally {
      setSaving(false);
    }
  };

  const handleTestGetProfile = async () => {
    try {
      setTestingEndpoint('GET /users/me');
      setActionError(null);
      const data = await api.getUserProfile();
      setApiResponse({
        endpoint: 'GET /users/me',
        status: 200,
        data,
      });
    } catch (err: any) {
      setApiResponse({
        endpoint: 'GET /users/me',
        status: err.status || 500,
        data: err.data || { error: err.message },
      });
    } finally {
      setTestingEndpoint(null);
    }
  };

  const handleTestBookingsDemo = async () => {
    try {
      setTestingEndpoint('GET /users/me/bookings-demo');
      setActionError(null);
      const data = await api.getUserBookingsDemo();
      setApiResponse({
        endpoint: 'GET /users/me/bookings-demo',
        status: 200,
        data,
      });
    } catch (err: any) {
      setApiResponse({
        endpoint: 'GET /users/me/bookings-demo',
        status: err.status || 500,
        data: err.data || { error: err.message },
      });
    } finally {
      setTestingEndpoint(null);
    }
  };

  const handleLogout = async () => {
    await signOut();
    onNavigate('login');
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
      {/* Page Title & Status Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-[#1e2a44]">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Account Profile</h1>
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Authenticated
            </span>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Supabase Auth user session synchronized with FastAPI & PostgreSQL
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshProfile()}
            disabled={profileLoading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#131b2e] hover:bg-[#1a253f] border border-[#22304d] text-xs font-semibold text-gray-200 transition-colors disabled:opacity-50"
            title="Refresh profile from PostgreSQL"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${profileLoading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600/10 hover:bg-rose-600/20 text-rose-400 border border-rose-500/30 text-xs font-bold transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>

      {actionError && (
        <div className="mb-6">
          <Alert type="error" message={actionError} onClose={() => setActionError(null)} />
        </div>
      )}

      {saveSuccess && (
        <div className="mb-6">
          <Alert type="success" message="Profile full name updated in PostgreSQL successfully!" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Profile Card */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-[#131b2e] rounded-3xl border border-[#22304d] p-6 shadow-xl relative overflow-hidden">
            {/* Ambient accent */}
            <div className="absolute top-0 right-0 w-32 h-32 bg-rose-500/10 rounded-full blur-2xl pointer-events-none" />

            <div className="flex flex-col items-center text-center">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-tr from-rose-600 to-amber-500 flex items-center justify-center text-white text-2xl font-bold shadow-lg shadow-rose-950 mb-4">
                {(profile?.full_name || user?.email || 'U').charAt(0).toUpperCase()}
              </div>

              <h2 className="text-xl font-bold text-white">
                {profile?.full_name || 'BookOurShow Customer'}
              </h2>
              <p className="text-xs text-gray-400 mt-0.5 truncate max-w-full">
                {user?.email}
              </p>

              <div className="mt-3 flex items-center gap-2">
                <span className="px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  {profile?.role || 'customer'}
                </span>
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#1a253f] text-gray-300 border border-[#2a3a5f]">
                  PostgreSQL
                </span>
              </div>
            </div>

            {/* Editable Full Name */}
            <div className="mt-6 pt-6 border-t border-[#1e2a44]">
              {editingName ? (
                <form onSubmit={handleUpdateName} className="space-y-3">
                  <label className="block text-xs font-bold text-gray-300">
                    Update Full Name (PUT /users/me)
                  </label>
                  <input
                    type="text"
                    value={fullNameInput}
                    onChange={(e) => setFullNameInput(e.target.value)}
                    className="w-full px-3 py-2 bg-[#0d1424] border border-[#22304d] focus:border-rose-500 rounded-lg text-xs text-white outline-none"
                    placeholder="Full name"
                    disabled={saving}
                  />
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={saving}
                      className="flex-1 py-1.5 px-3 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
                    >
                      {saving ? <LoadingSpinner size="sm" /> : <Save className="w-3.5 h-3.5" />}
                      <span>Save</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingName(false)}
                      disabled={saving}
                      className="px-3 py-1.5 bg-[#1a253f] hover:bg-[#22304d] text-gray-300 rounded-lg text-xs font-semibold"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-[11px] text-gray-400 font-medium">Display Name</div>
                    <div className="text-xs font-semibold text-white mt-0.5">
                      {profile?.full_name || 'Not set'}
                    </div>
                  </div>
                  <button
                    onClick={() => setEditingName(true)}
                    className="text-xs text-rose-400 hover:text-rose-300 font-semibold"
                  >
                    Edit
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Security Summary Badge */}
          <div className="bg-[#131b2e] rounded-3xl border border-[#22304d] p-5 text-xs text-gray-400 space-y-3">
            <div className="flex items-center gap-2 font-bold text-white">
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>Security Architecture</span>
            </div>
            <p className="leading-relaxed">
              • Passwords managed exclusively by Supabase Auth (never stored in FastAPI).
            </p>
            <p className="leading-relaxed">
              • Database roles read from trusted PostgreSQL <code className="text-rose-300">public.profiles</code> records.
            </p>
            <p className="leading-relaxed">
              • Tokens verified per-request using Supabase JWT verification.
            </p>
          </div>
        </div>

        {/* Right Column: Database Profile & FastAPI API Test Deck */}
        <div className="lg:col-span-2 space-y-6">
          {/* Identity Metadata Details */}
          <div className="bg-[#131b2e] rounded-3xl border border-[#22304d] p-6 shadow-xl">
            <h3 className="text-sm font-bold uppercase tracking-wider text-gray-400 mb-4 flex items-center gap-2">
              <Key className="w-4 h-4 text-rose-400" />
              <span>Identity & Token Credentials</span>
            </h3>

            <div className="space-y-4">
              <div>
                <div className="text-xs text-gray-400 font-medium">Supabase Auth User ID (UUID)</div>
                <div className="mt-1 font-mono text-xs text-rose-300 bg-[#0d1424] px-3 py-2 rounded-xl border border-[#22304d] break-all select-all">
                  {user?.id || 'N/A'}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-400 font-medium">Email Address</div>
                  <div className="mt-1 text-xs text-gray-200 bg-[#0d1424] px-3 py-2 rounded-xl border border-[#22304d] flex items-center justify-between">
                    <span className="truncate">{user?.email || 'N/A'}</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 ml-1.5" />
                  </div>
                </div>

                <div>
                  <div className="text-xs text-gray-400 font-medium">PostgreSQL Role</div>
                  <div className="mt-1 text-xs text-gray-200 bg-[#0d1424] px-3 py-2 rounded-xl border border-[#22304d] flex items-center justify-between">
                    <span className="font-semibold capitalize text-amber-400">{profile?.role || 'customer'}</span>
                    <span className="text-[10px] text-gray-400">Strict RBAC</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive FastAPI API Inspector */}
          <div className="bg-[#131b2e] rounded-3xl border border-[#22304d] p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-rose-400" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-gray-300">
                  Live FastAPI Integration Deck
                </h3>
              </div>
              <span className="text-[11px] text-gray-400">Bearer Token Attached</span>
            </div>

            <p className="text-xs text-gray-400 mb-5 leading-relaxed">
              Verify end-to-end communication: click below to trigger protected FastAPI endpoints using the current active Supabase JWT.
            </p>

            <div className="flex flex-wrap gap-3 mb-6">
              <button
                onClick={handleTestGetProfile}
                disabled={testingEndpoint !== null}
                className="px-4 py-2.5 bg-rose-600/10 hover:bg-rose-600/20 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-bold transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {testingEndpoint === 'GET /users/me' ? (
                  <LoadingSpinner size="sm" className="text-rose-400" />
                ) : (
                  <User className="w-3.5 h-3.5" />
                )}
                <span>Test GET /users/me</span>
              </button>

              <button
                onClick={handleTestBookingsDemo}
                disabled={testingEndpoint !== null}
                className="px-4 py-2.5 bg-[#18233d] hover:bg-[#202f52] text-gray-200 border border-[#2d3f66] rounded-xl text-xs font-bold transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {testingEndpoint === 'GET /users/me/bookings-demo' ? (
                  <LoadingSpinner size="sm" className="text-gray-300" />
                ) : (
                  <Ticket className="w-3.5 h-3.5" />
                )}
                <span>Test Bookings Isolation Demo</span>
              </button>
            </div>

            {/* Response Console */}
            {apiResponse && (
              <div className="rounded-2xl bg-[#090d16] border border-[#1f2b45] p-4 text-xs font-mono overflow-hidden">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#1b253b] text-[11px]">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-rose-400">{apiResponse.endpoint}</span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      apiResponse.status >= 200 && apiResponse.status < 300
                        ? 'bg-emerald-500/20 text-emerald-300'
                        : 'bg-red-500/20 text-red-300'
                    }`}>
                      HTTP {apiResponse.status}
                    </span>
                  </div>
                  <span className="text-gray-500">FastAPI Response</span>
                </div>
                <pre className="text-gray-300 max-h-56 overflow-auto leading-relaxed">
                  {JSON.stringify(apiResponse.data, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
