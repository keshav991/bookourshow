import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/api';
import { useAuth } from '../context/AuthContext';

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
let checkoutScriptPromise;

function loadCheckoutScript() {
  if (window.Razorpay) return Promise.resolve();
  if (!checkoutScriptPromise) {
    checkoutScriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.onload = resolve;
      script.onerror = () => { checkoutScriptPromise = null; reject(new Error('Could not load secure checkout. Try again.')); };
      document.body.appendChild(script);
    });
  }
  return checkoutScriptPromise;
}

export function BookingDetailsPage() {
  const { bookingId } = useParams();
  const { session } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [booking, setBooking] = useState(location.state?.booking || null);
  const [error, setError] = useState('');
  const [paymentError, setPaymentError] = useState('');
  const [paying, setPaying] = useState(false);
  const [cashBusy, setCashBusy] = useState(false);
  const paymentRequestKey = useRef(null);
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

  async function payForBooking() {
    if (!booking || !session?.access_token || paying || cashBusy) return;
    setPaying(true); setPaymentError('');
    paymentRequestKey.current ||= crypto.randomUUID();
    try {
      const order = await apiRequest(`/bookings/${booking.id}/payments/order`, session.access_token, {
        method: 'POST', body: JSON.stringify({ idempotency_key: paymentRequestKey.current }),
      });
      setBooking(await apiRequest(`/bookings/${booking.id}`, session.access_token));
      await loadCheckoutScript();
      const checkout = new window.Razorpay({
        key: order.key_id,
        amount: Math.round(Number(order.amount) * 100),
        currency: order.currency,
        name: 'BookOurShow',
        description: `Booking ${booking.booking_reference}`,
        order_id: order.provider_order_id,
        prefill: { email: session.user?.email || '' },
        theme: { color: '#e53935' },
        handler: async (result) => {
          try {
            await apiRequest(`/bookings/${booking.id}/payments/verify`, session.access_token, {
              method: 'POST',
              body: JSON.stringify({
                provider_order_id: result.razorpay_order_id,
                provider_payment_id: result.razorpay_payment_id,
                signature: result.razorpay_signature,
              }),
            });
            paymentRequestKey.current = null;
            const refreshed = await apiRequest(`/bookings/${booking.id}`, session.access_token);
            setBooking(refreshed);
          } catch (reason) {
            setPaymentError(`${reason.message} Your payment is being checked; refresh this page before retrying.`);
          } finally { setPaying(false); }
        },
        modal: { ondismiss: () => setPaying(false) },
      });
      checkout.on('payment.failed', (result) => {
        setPaymentError(result.error?.description || 'Payment did not complete. You can try again.');
        paymentRequestKey.current = crypto.randomUUID();
        setPaying(false);
        checkout.close();
      });
      checkout.open();
    } catch (reason) {
      setPaymentError(reason.message);
      setPaying(false);
    }
  }

  async function payWithCash() {
    if (!booking || !session?.access_token || paying || cashBusy) return;
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

  const isBusy = paying || cashBusy;
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
        <dl>
          <div><dt>Reference</dt><dd>{booking.booking_reference}</dd></div>
          <div><dt>Status</dt><dd>{booking.status}</dd></div>
          {booking.payment_method && <div><dt>Payment</dt><dd>{booking.payment_method}</dd></div>}
          <div><dt>Seats</dt><dd>{booking.seats.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ') || '—'}</dd></div>
          <div><dt>Total</dt><dd>{money.format(Number(booking.total_amount))}</dd></div>
        </dl>

        {isPending && (
          <p>Choose your payment method below. You can pay online via Razorpay or choose Cash to pay at the counter before the show.</p>
        )}
        {isConfirmed && (
          <p>Keep this booking reference for your ticket.</p>
        )}
        {!isPending && !isConfirmed && (
          <p className="booking-summary__error" role="alert">
            This booking is {String(booking.status || '').toLowerCase()}. The hold has expired or was cancelled, so payment is no longer accepted.
          </p>
        )}

        {paymentError && <p className="booking-summary__error" role="alert">{paymentError}</p>}

        {isPending && (
          <div className="booking-payment-buttons" role="group" aria-label="Payment options">
            <button
              type="button"
              className="button button--primary"
              disabled={isBusy}
              onClick={payForBooking}
            >
              {paying ? 'Opening secure checkout…' : '💳 Pay Securely with Razorpay'}
            </button>
            <button
              type="button"
              className="button button--cash"
              disabled={isBusy}
              onClick={payWithCash}
            >
              {cashBusy ? 'Confirming cash booking…' : '💵 Cash (Pay at Counter)'}
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
