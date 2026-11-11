import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthFrame, AuthMessage } from '../components/AuthFrame';
import { supabase, supabaseConfigError } from '../lib/supabase';

export function ResetPasswordPage() {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [message, setMessage] = useState('');
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function submit(event) {
    event.preventDefault(); setMessage('');
    if (!supabase) { setMessage(supabaseConfigError); return; }
    if (password.length < 8 || password !== confirm) { setMessage(password.length < 8 ? 'Use at least 8 characters.' : 'The passwords do not match.'); return; }
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) setMessage(error.message);
    else { setSuccess(true); setMessage('Your password has been updated.'); setTimeout(() => navigate('/profile', { replace: true }), 1200); }
  }
  return <AuthFrame title="Choose a new password" subtitle="Set a new password for your account.">
    <AuthMessage type={success ? 'success' : 'error'}>{message}</AuthMessage>
    {!success ? <form className="auth-form" onSubmit={submit}>
      <label>New password<input type="password" autoComplete="new-password" minLength="8" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
      <label>Confirm new password<input type="password" autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} /></label>
      <button className="button button--primary auth-submit" disabled={busy}>{busy ? 'Updating…' : 'Update password'}</button>
    </form> : <Link className="text-link" to="/login">Return to sign in</Link>}
  </AuthFrame>;
}
