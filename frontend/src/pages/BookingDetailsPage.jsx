import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/api';
import { useAuth } from '../context/AuthContext';

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });

export function BookingDetailsPage() {
  const { bookingId } = useParams();
  const { session } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [booking, setBooking] = useState(location.state?.booking || null);
  const [error, setError] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [cashBusy, setCashBusy] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const cashIdempotencyKey = useRef(null);

  useEffect(() => {
    if (!session?.access_token) return;
    let active = true;
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
    const prompt = confirmedCash
      ? 'Cancel this cash ticket? The booking and QR ticket will become invalid. Any counter refund must be handled by theatre staff.'
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
    <main className="page-container show-page">
      <span className="eyebrow eyebrow--red">
        {isConfirmed ? 'Booking confirmed' : 'Booking created'}
      </span>
      <h1 className="booking-title">
        {isConfirmed ? 'Your tickets are confirmed' : 'Your seats are on hold'}
      </h1>
      <section className="show-detail-card booking-detail-card">
        {isPending && (
          <p>Your seats are reserved until {booking.expires_at ? new Date(booking.expires_at).toLocaleString('en-IN') : 'the hold expires'}.</p>
        )}
        {isPending && (
          <button type="button" className="button button--quiet" disabled={isBusy || cancelling} onClick={cancelBooking}>
            {cancelling ? 'Cancelling…' : 'Cancel booking'}
          </button>
        )}
        {isConfirmed && booking.payment_method === 'CASH' && <p>Cash tickets can be cancelled before the showtime cutoff. Any refund for cash already collected must be handled by theatre staff.</p>}
        {isConfirmed && booking.payment_method === 'CASH' && (
          <button type="button" className="button button--quiet" disabled={cancelling} onClick={cancelBooking}>
            {cancelling ? 'Cancelling…' : 'Cancel ticket'}
          </button>
        )}
        <dl>
          <div><dt>Reference</dt><dd>{booking.booking_reference}</dd></div>
          <div><dt>Status</dt><dd>{booking.status}</dd></div>
          {booking.payment_method && <div><dt>Payment</dt><dd>{booking.payment_method}</dd></div>}
          <div><dt>Seats</dt><dd>{booking.seats.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ') || '—'}</dd></div>
          <div><dt>Total</dt><dd>{money.format(Number(booking.total_amount))}</dd></div>
        </dl>

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

        {isConfirmed && (
          <Link className="button button--primary" to={`/ticket/${booking.id}`}>
            View ticket
          </Link>
        )}
      </section>
      <Link className="button button--primary booking-profile-link" to="/profile">View your bookings</Link>
    </main>
  );
}
