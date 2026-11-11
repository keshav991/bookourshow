import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { AuthFrame, AuthMessage } from '../components/AuthFrame';
import { useAuth } from '../context/AuthContext';
import { supabase } from '../lib/supabase';

export function RegisterPage() {
  const { user, configured, configError } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  if (user) return <Navigate to="/" replace />;

  async function submit(event) {
    event.preventDefault(); setMessage('');
    if (password.length < 8) { setMessage('Choose a password with at least 8 characters.'); return; }
    if (password !== confirm) { setMessage('The passwords do not match.'); return; }
    setBusy(true);
    try {
      const { data, error } = await supabase.auth.signUp({
        email: email.trim(), password,
        options: { data: { full_name: fullName.trim() }, emailRedirectTo: `${window.location.origin}/auth/callback` },
      });
      if (error) setMessage(error.message);
      else if (!data.session) setSuccess(true);
      else window.location.assign('/');
    } catch (error) { setMessage(error.message || 'Could not create your account. Check your connection and try again.'); }
    finally { setBusy(false); }
  }
  async function google() {
    setBusy(true);
    try {
      const { error } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: `${window.location.origin}/auth/callback` } });
      if (error) setMessage(error.message);
    } catch (error) { setMessage(error.message || 'Could not start Google sign-in.'); }
    finally { setBusy(false); }
  }

  return <AuthFrame title="Create your account" subtitle="One account for all your movie discoveries.">
    {!configured ? <AuthMessage>{configError}</AuthMessage> : null}
    {success ? <AuthMessage type="success">Account created. Check your email to verify your address, then come back to sign in.</AuthMessage> : null}
    <AuthMessage>{message}</AuthMessage>
    <button className="auth-google" type="button" disabled={busy || !configured} onClick={google}><GoogleMark />Continue with Google</button>
    <div className="auth-divider"><span>or register with email</span></div>
    <form className="auth-form" onSubmit={submit}>
      <label>Full name<input autoComplete="name" required maxLength="150" value={fullName} onChange={(e) => setFullName(e.target.value)} /></label>
      <label>Email address<input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label>Password<input type="password" autoComplete="new-password" required minLength="8" value={password} onChange={(e) => setPassword(e.target.value)} /><small>Use at least 8 characters.</small></label>
      <label>Confirm password<input type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} /></label>
      <button className="button button--primary auth-submit" disabled={busy || !configured}>{busy ? 'Creating account…' : 'Create account'}</button>
    </form>
    <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
  </AuthFrame>;
}

function GoogleMark() { return <svg aria-hidden="true" viewBox="0 0 48 48" width="18" height="18"><path fill="#FFC107" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5h6.6c3.9-3.6 6.1-8.8 6.1-14.9Z"/><path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.8l-6.6-5c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.5H5.8v5.2A20 20 0 0 0 24 44Z"/><path fill="#4A90E2" d="M12.6 27.7a12 12 0 0 1 0-7.4v-5.2H5.8a20 20 0 0 0 0 17.8l6.8-5.2Z"/><path fill="#EA4335" d="M24 11.8c3 0 5.6 1 7.7 3.1l5.8-5.8A19.5 19.5 0 0 0 24 4 20 20 0 0 0 5.8 15.1l6.8 5.2c1.6-4.9 6.1-8.5 11.4-8.5Z"/></svg>; }
