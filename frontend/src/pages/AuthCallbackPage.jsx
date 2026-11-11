import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthFrame, AuthMessage } from '../components/AuthFrame';
import { supabase, supabaseConfigError } from '../lib/supabase';

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    if (!supabase) { setError(supabaseConfigError); return () => { active = false; }; }
    supabase.auth.getSession().then(({ data, error: authError }) => {
      if (!active) return;
      if (authError) setError(authError.message);
      else if (data.session) navigate('/', { replace: true });
      else setError('No active session was found. The sign-in link may have expired.');
    }).catch((reason) => { if (active) setError(reason.message); });
    return () => { active = false; };
  }, [navigate]);
  return <AuthFrame title={error ? 'Sign-in link unavailable' : 'Completing sign in'} subtitle="We are confirming your secure account session.">
    {error ? <><AuthMessage>{error}</AuthMessage><Link className="text-link" to="/login">Return to sign in</Link></> : <p role="status">Please wait…</p>}
  </AuthFrame>;
}
