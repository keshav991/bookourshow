import { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/api';
import { useAuth } from '../context/AuthContext';

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
const istDateTime = (value) => new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
const istDate = (value) => new Date(value).toLocaleDateString('en-IN', {
  timeZone: 'Asia/Kolkata', weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
});
const istTime = (value) => new Date(value).toLocaleTimeString('en-IN', {
  timeZone: 'Asia/Kolkata', hour: 'numeric', minute: '2-digit',
});

export function BookingDetailsPage() {
  const { bookingId } = useParams();
  const { session } = useAuth();
  const navigate = useNavigate();
  const [booking, setBooking] = useState(null);
  const [error, setError] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [cashBusy, setCashBusy] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const cashIdempotencyKey = useRef(null);

  useEffect(() => {
    if (!session?.access_token) return;
    let active = true;
    setBooking(null);
    setError('');
    apiRequest(`/bookings/${bookingId}`, session.access_token)
      .then((value) => {
        if (active) {
          setBooking(value);
          setError('');
        }
      })
      .catch((reason) => {
        if (active) setError(reason.message);
      });
    return () => { active = false; };
  }, [bookingId, session?.access_token]);

  async function payWithCash() {
    if (!booking || !session?.access_token || cashBusy) return;
    setCashBusy(true); setPaymentError('');
    cashIdempotencyKey.current ||= crypto.randomUUID();
    try {
      // POST to cash-confirmation; on success navigate to the ticket page
      await apiRequest(`/bookings/${booking.id}/cash-confirmation`, session.access_token, {
        method: 'POST',
        body: JSON.stringify({ idempotency_key: cashIdempotencyKey.current }),
      });
      navigate(`/ticket/${booking.id}`);
    } catch (reason) {
      setPaymentError(reason.message);
      cashIdempotencyKey.current = null;
    } finally {
      setCashBusy(false);
    }
  }

  async function cancelBooking() {
    if (!booking || !session?.access_token || cancelling) return;
    const confirmedCash = String(booking.status).toUpperCase() === 'CONFIRMED' && booking.payment_method === 'CASH';
    const cutoffText = booking.cancellation_cutoff_at
      ? ` Cancellation is available until ${istDateTime(booking.cancellation_cutoff_at)} IST.`
      : '';
    const prompt = confirmedCash
      ? `Cancel this cash ticket? The booking and QR ticket will become invalid.${cutoffText} Any counter refund must be handled by theatre staff.`
      : 'Cancel this pending booking and release its seats?';
    if (!window.confirm(prompt)) return;
    setCancelling(true); setError(''); setPaymentError('');
    try {
      const updated = await apiRequest(`/bookings/${booking.id}/cancel`, session.access_token, { method: 'POST' });
      setBooking(updated);
    } catch (reason) {
      setError(reason.message);
    } finally { setCancelling(false); }
  }

  if (error) return (
    <main className="page-container show-page">
      <div className="shows-error">
        <h1>Could not load booking</h1>
        <p>{error}</p>
        <Link className="button button--primary" to="/profile">Go to your profile</Link>
      </div>
    </main>
  );
  if (!booking) return <main className="page-container show-page" role="status">Loading booking…</main>;

  const isBusy = cashBusy;
  const isPending = String(booking.status || '').toUpperCase() === 'PENDING';
  const isConfirmed = String(booking.status || '').toUpperCase() === 'CONFIRMED';

  return (
    <main className="page-container show-page booking-details-page">
      <span className="eyebrow eyebrow--red">Booking details</span>
      <h1 className="booking-title">{isConfirmed ? 'Your booking is confirmed' : 'Your booking'}</h1>
      <section className="booking-detail-card">
        <div className="booking-movie-panel">
          <img
            className="booking-movie-poster"
            src={booking.movie?.poster_url || '/images/poster-fallback.svg'}
            alt={booking.movie?.title ? `${booking.movie.title} poster` : 'Movie poster unavailable'}
            onError={(event) => { event.currentTarget.src = '/images/poster-fallback.svg'; }}
          />
          <div className="booking-movie-copy">
            <span className="eyebrow">Movie</span>
            <h2>{booking.movie?.title || 'Movie details unavailable'}</h2>
            <div className="booking-movie-meta">
              {booking.movie?.language && <span>{booking.movie.language}</span>}
              {booking.movie?.duration_minutes && <span>{booking.movie.duration_minutes} min</span>}
              {booking.movie?.certification && <span>{booking.movie.certification}</span>}
            </div>
            {booking.movie?.title && booking.show?.language && booking.show.language !== booking.movie.language && (
              <p className="booking-show-language">Show language: {booking.show.language}</p>
            )}
          </div>
        </div>

        <section className="booking-info-section" aria-labelledby="booking-show-heading">
          <h2 id="booking-show-heading">Showtime</h2>
          {booking.show ? (
            <dl className="booking-info-grid">
              <div><dt>Date</dt><dd>{istDate(booking.show.start_time)}</dd></div>
              <div><dt>Time</dt><dd>{istTime(booking.show.start_time)} – {istTime(booking.show.end_time)} IST</dd></div>
              <div><dt>Theatre</dt><dd>{booking.show.theatre_name}</dd></div>
              <div><dt>Location</dt><dd>{booking.show.theatre_address}, {booking.show.city_name}</dd></div>
              <div><dt>Screen</dt><dd>{booking.show.screen_name}</dd></div>
            </dl>
          ) : <p className="booking-detail-muted">Show information is unavailable.</p>}
        </section>

        <section className="booking-info-section" aria-labelledby="booking-summary-heading">
          <h2 id="booking-summary-heading">Booking summary</h2>
          <dl className="booking-info-grid booking-info-grid--summary">
            <div><dt>Booking reference</dt><dd>{booking.booking_reference}</dd></div>
            <div><dt>Booking status</dt><dd><span className={`booking-status booking-status--${String(booking.status).toLowerCase()}`}>{booking.status}</span></dd></div>
            <div><dt>Payment method</dt><dd>{booking.payment_method || (isPending ? 'Cash (Pay at Counter)' : '—')}</dd></div>
            <div><dt>Payment status</dt><dd>{booking.payment_status || (isPending ? 'PENDING_PAYMENT' : '—')}</dd></div>
            <div><dt>Selected seats</dt><dd>{booking.seats.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ') || '—'}</dd></div>
            <div><dt>Number of seats</dt><dd>{booking.seats.length}</dd></div>
            <div><dt>Total amount</dt><dd>{money.format(Number(booking.total_amount))}</dd></div>
            <div><dt>Booking created</dt><dd>{istDateTime(booking.created_at)} IST</dd></div>
          </dl>
        </section>

        {isPending && (
          <p>Your seats are reserved until {booking.expires_at ? `${istDateTime(booking.expires_at)} IST` : 'the hold expires'}.</p>
        )}
        {isPending && (
          <button type="button" className="button button--quiet" disabled={isBusy || cancelling} onClick={cancelBooking}>
            {cancelling ? 'Cancelling…' : 'Cancel booking'}
          </button>
        )}
        {isConfirmed && booking.payment_method === 'CASH' && <p>Cash tickets can be cancelled until {booking.cancellation_cutoff_at ? `${istDateTime(booking.cancellation_cutoff_at)} IST` : 'the configured showtime cutoff'}. Any refund for cash already collected must be handled by theatre staff.</p>}
        {isConfirmed && booking.payment_method === 'CASH' && (
          <button type="button" className="button button--quiet" disabled={cancelling} onClick={cancelBooking}>
            {cancelling ? 'Cancelling…' : 'Cancel ticket'}
          </button>
        )}
        {isPending && (
          <p>Confirm your booking with Cash (Pay at Counter). Payment remains pending until theatre staff records collection.</p>
        )}
        {isConfirmed && (
          <p>Keep this booking reference for your ticket.</p>
        )}
        {!isPending && !isConfirmed && (
          <p className="booking-summary__error" role="alert">
            {booking.status === 'CANCELLED'
              ? 'This booking was cancelled. Its seats have been released and can be booked again.'
              : 'This booking has expired, so it can no longer be confirmed.'}
          </p>
        )}

        {paymentError && <p className="booking-summary__error" role="alert">{paymentError}</p>}

        {isPending && (
          <div className="booking-payment-buttons" role="group" aria-label="Cash payment option">
            <button
              type="button"
              className="button button--cash"
              disabled={isBusy}
              onClick={payWithCash}
            >
              {cashBusy ? 'Confirming cash booking…' : 'Confirm Cash Booking'}
            </button>
          </div>
        )}

        {isConfirmed && booking.ticket_valid && (
          <Link className="button button--primary" to={`/ticket/${booking.id}`}>
            View ticket
          </Link>
        )}
        {isConfirmed && !booking.ticket_valid && <p className="booking-detail-muted">Ticket details are not available for this booking.</p>}
      </section>
      <Link className="button button--primary booking-profile-link" to="/profile">View your bookings</Link>
    </main>
  );
}
