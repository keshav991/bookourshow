import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { apiRequest } from '../lib/api';
import { supabase, supabaseConfigError } from '../lib/supabase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState('');

  useEffect(() => {
    if (!supabase) { setLoading(false); return undefined; }
    let mounted = true;
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (mounted) {
        setSession(nextSession);
        setProfile(null);
        setProfileError('');
        setLoading(false);
      }
    });
    supabase.auth.getSession().then(({ data, error }) => {
      if (!mounted) return;
      if (error) setProfileError(error.message);
      setSession(data.session);
      setLoading(false);
    }).catch((error) => { if (mounted) { setProfileError(error.message); setLoading(false); } });
    return () => { mounted = false; subscription.unsubscribe(); };
  }, []);

  useEffect(() => {
    if (!session?.access_token) { setProfile(null); return undefined; }
    let active = true;
    setProfileLoading(true);
    apiRequest('/users/me', session.access_token)
      .then((data) => { if (active) { setProfile(data); setProfileError(''); } })
      .catch((error) => { if (active) { setProfileError(error.message); setProfile(null); } })
      .finally(() => { if (active) setProfileLoading(false); });
    return () => { active = false; };
  }, [session?.access_token]);

  const refreshProfile = useCallback(async () => {
    if (!session?.access_token) return null;
    setProfileLoading(true);
    try {
      const nextProfile = await apiRequest('/users/me', session.access_token);
      setProfile(nextProfile); setProfileError(''); return nextProfile;
    } catch (error) { setProfileError(error.message); throw error; }
    finally { setProfileLoading(false); }
  }, [session?.access_token]);

  const value = {
    session, user: session?.user ?? null, profile, profileLoading, profileError,
    loading, configured: Boolean(supabase), configError: supabaseConfigError,
    refreshProfile,
    signOut: async () => {
      if (!supabase) return { error: new Error(supabaseConfigError) };
      // Ask the API to revoke this user's session, then always clear the browser copy.
      if (session?.access_token) {
        try { await apiRequest('/auth/logout', session.access_token, { method: 'POST' }); }
        catch { /* Local sign out still works when the API is unavailable. */ }
      }
      const result = await supabase.auth.signOut({ scope: 'local' });
      if (result.error) throw result.error;
      setSession(null); setProfile(null);
      return result;
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
