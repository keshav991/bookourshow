import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/api';
import { useAuth } from '../context/AuthContext';

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });

export function BookingDetailsPage() {
  const { bookingId } = useParams();
  const { session } = useAuth();
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    apiRequest(`/bookings/${bookingId}`, session?.access_token)
      .then((value) => { if (active) setBooking(value); })
      .catch((reason) => { if (active) setError(reason.message); });
    return () => { active = false; };
  }, [bookingId, session?.access_token]);

  if (error) return <main className="page-container show-page"><div className="shows-error"><h1>Could not load booking</h1><p>{error}</p><Link className="button button--primary" to="/profile">Go to your profile</Link></div></main>;
  if (!booking) return <main className="page-container show-page" role="status">Loading booking…</main>;

  return <main className="page-container show-page">
    <span className="eyebrow eyebrow--red">Booking created</span>
    <h1 className="booking-title">Your seats are on hold</h1>
    <section className="show-detail-card booking-detail-card">
      <p>Your booking is pending payment. The seats are reserved until {booking.expires_at ? new Date(booking.expires_at).toLocaleString('en-IN') : 'the hold expires'}.</p>
      <dl>
        <div><dt>Reference</dt><dd>{booking.booking_reference}</dd></div>
        <div><dt>Status</dt><dd>{booking.status}</dd></div>
        <div><dt>Seats</dt><dd>{booking.seats.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ') || '—'}</dd></div>
        <div><dt>Total</dt><dd>{money.format(Number(booking.total_amount))}</dd></div>
      </dl>
      <p>Online payment will be added in Phase 3.3. Your seat hold will expire automatically if you leave this booking unpaid.</p>
    </section>
    <Link className="button button--primary booking-profile-link" to="/profile">View your bookings</Link>
  </main>;
}
