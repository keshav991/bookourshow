import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthMessage } from '../components/AuthFrame';
import { useAuth } from '../context/AuthContext';
import { apiRequest } from '../lib/api';

export function ProfilePage() {
  const { user, session, profile, profileLoading, profileError, refreshProfile, signOut } = useAuth();
  const [name, setName] = useState(null);
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);
  const [bookings, setBookings] = useState([]);
  const [bookingError, setBookingError] = useState('');
  const [cancellingId, setCancellingId] = useState(null);
  const navigate = useNavigate();
  const fullName = profile?.full_name ?? user?.user_metadata?.full_name ?? '';

  useEffect(() => {
    let active = true;
    if (!session?.access_token) return undefined;
    apiRequest('/bookings/me', session.access_token)
      .then((items) => { if (active) setBookings(items); })
      .catch((error) => { if (active) setBookingError(error.message); });
    return () => { active = false; };
  }, [session?.access_token]);

  async function cancelBooking(bookingId) {
    setCancellingId(bookingId); setBookingError('');
    try {
      const updated = await apiRequest(`/bookings/${bookingId}/cancel`, session.access_token, { method: 'POST' });
      setBookings((items) => items.map((item) => item.id === bookingId ? updated : item));
    } catch (error) { setBookingError(error.message); }
    finally { setCancellingId(null); }
  }

  async function updateName(event) {
    event.preventDefault(); setSaving(true); setMessage('');
    try {
      await apiRequest('/users/me', session.access_token, { method: 'PUT', body: JSON.stringify({ full_name: (name ?? fullName).trim() }) });
      await refreshProfile(); setMessage('Your profile has been updated.');
    } catch (error) { setMessage(error.message); }
    finally { setSaving(false); }
  }
  async function logout() {
    try { await signOut(); navigate('/', { replace: true }); }
    catch (error) { setMessage(error.message); }
  }
  return <main className="page-container profile-page">
    <header className="profile-heading"><span className="eyebrow eyebrow--red">Your account</span><h1>Profile</h1><p>Manage your BookOurShow account details.</p></header>
    {profileError ? <AuthMessage>{profileError} — check that the backend and profile database are available.</AuthMessage> : null}
    {message ? <AuthMessage type={message.includes('updated') ? 'success' : 'error'}>{message}</AuthMessage> : null}
    <section className="profile-card">
      <div className="profile-avatar" aria-hidden="true">{(fullName || user?.email || 'U').slice(0, 1).toUpperCase()}</div>
      <div className="profile-details"><span className="eyebrow eyebrow--red">Account details</span>
        <dl><div><dt>Full name</dt><dd>{profileLoading ? 'Loading…' : fullName || 'Not set'}</dd></div><div><dt>Email address</dt><dd>{user?.email}</dd></div><div><dt>Member since</dt><dd>{user?.created_at ? new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }) : '—'}</dd></div><div><dt>Role</dt><dd>{profile?.role || (profileLoading ? 'Loading…' : 'Unavailable')}</dd></div></dl>
      </div>
    </section>
    <section className="profile-card profile-edit"><div><h2>Edit your name</h2><p>Your role and access are managed securely by BookOurShow.</p></div>
      <form className="auth-form" onSubmit={updateName}><label>Full name<input required maxLength="150" value={name ?? fullName} onChange={(event) => setName(event.target.value)} /></label><button className="button button--primary" disabled={saving || !session?.access_token}>{saving ? 'Saving…' : 'Save changes'}</button></form>
    </section>
    <section className="profile-bookings">
      <header><h2>Your bookings</h2><p>Booking history is private to your account.</p></header>
      {bookingError ? <AuthMessage type="error">{bookingError}</AuthMessage> : null}
      {bookings.length === 0 && !bookingError ? <p>No bookings yet.</p> : null}
      {bookings.map((booking) => <article className="profile-booking" key={booking.id}>
        <div><strong>{booking.booking_reference}</strong><span>{booking.seats.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ')} · ₹{Number(booking.total_amount).toFixed(2)}</span><small>{booking.status} · {new Date(booking.created_at).toLocaleString()}</small></div>
        <div><button className="button button--quiet" type="button" onClick={() => navigate(`/booking/${booking.id}`)}>View</button>
          {booking.status === 'PENDING' ? <button className="button button--quiet" type="button" disabled={cancellingId === booking.id} onClick={() => cancelBooking(booking.id)}>{cancellingId === booking.id ? 'Cancelling…' : 'Cancel'}</button> : null}</div>
      </article>)}
    </section>
    <button type="button" className="profile-signout" onClick={logout}>Sign out</button>
  </main>;
}
