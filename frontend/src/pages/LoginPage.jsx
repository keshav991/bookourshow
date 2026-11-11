import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AuthFrame, AuthMessage } from '../components/AuthFrame';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';

export function LoginPage() {
  const { user, configured, configError } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  if (user) return <Navigate to={location.state?.from || '/'} replace />;

  async function submit(event) {
    event.preventDefault(); setMessage(''); setBusy(true);
    try {
      const { error } = await supabase.auth.signInWithPassword({ email: email.trim(), password });
      if (error) setMessage(error.message); else navigate(location.state?.from || '/', { replace: true });
    } catch (error) { setMessage(error.message || 'Could not sign in. Check your connection and try again.'); }
    finally { setBusy(false); }
  }
  async function google() {
    setMessage(''); setBusy(true);
    try {
      const { error } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: `${window.location.origin}/auth/callback` } });
      if (error) setMessage(error.message);
    } catch (error) { setMessage(error.message || 'Could not start Google sign-in.'); }
    finally { setBusy(false); }
  }
  async function forgotPassword() {
    if (!email.trim()) { setMessage('Enter your email address first, then choose Forgot password.'); return; }
    setBusy(true); setMessage('');
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: `${window.location.origin}/reset-password` });
      setMessage(error ? error.message : 'If an account exists for that email, a password reset link is on its way.');
    } catch (error) { setMessage(error.message || 'Could not send the password reset email.'); }
    finally { setBusy(false); }
  }

  return <AuthFrame title="Welcome back" subtitle="Sign in to manage your BookOurShow account.">
    {!configured ? <AuthMessage>{configError}</AuthMessage> : null}
    <AuthMessage>{message}</AuthMessage>
    <button className="auth-google" type="button" disabled={busy || !configured} onClick={google}><GoogleMark />Continue with Google</button>
    <div className="auth-divider"><span>or sign in with email</span></div>
    <form className="auth-form" onSubmit={submit}>
      <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label>Password<input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      <button className="auth-forgot" type="button" onClick={forgotPassword} disabled={busy || !configured}>Forgot password?</button>
      <button className="button button--primary auth-submit" disabled={busy || !configured}>{busy ? 'Please wait…' : 'Sign in'}</button>
    </form>
    <p className="auth-switch">New to BookOurShow? <Link to="/register">Create an account</Link></p>
  </AuthFrame>;
}

function GoogleMark() { return <svg aria-hidden="true" viewBox="0 0 48 48" width="18" height="18"><path fill="#FFC107" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5h6.6c3.9-3.6 6.1-8.8 6.1-14.9Z"/><path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.8l-6.6-5c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.5H5.8v5.2A20 20 0 0 0 24 44Z"/><path fill="#4A90E2" d="M12.6 27.7a12 12 0 0 1 0-7.4v-5.2H5.8a20 20 0 0 0 0 17.8l6.8-5.2Z"/><path fill="#EA4335" d="M24 11.8c3 0 5.6 1 7.7 3.1l5.8-5.8A19.5 19.5 0 0 0 24 4 20 20 0 0 0 5.8 15.1l6.8 5.2c1.6-4.9 6.1-8.5 11.4-8.5Z"/></svg>; }
