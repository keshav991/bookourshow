import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { apiRequest } from '../lib/api';

export function TicketVerifyPage() {
  const { token } = useParams();
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest(`/tickets/verify/${encodeURIComponent(token)}`)
      .then((data) => { setResult(data); setLoading(false); })
      .catch((reason) => { setError(reason.message); setLoading(false); });
  }, [token]);

  if (loading) return <main className="page-container show-page" role="status"><p>Verifying ticket…</p></main>;

  if (error) {
    return (
      <main className="page-container show-page">
        <div className="shows-error">
          <h1>Ticket not found</h1>
          <p>{error}</p>
          <Link className="button button--primary" to="/">Go home</Link>
        </div>
      </main>
    );
  }

  const isValid = result?.is_valid;

  return (
    <main className="page-container show-page ticket-verify-page">
      <div className={`ticket-verify-card ${isValid ? 'ticket-verify-card--valid' : 'ticket-verify-card--invalid'}`}>
        <div className="ticket-verify-icon">{isValid ? '✅' : '⚠️'}</div>
        <h1 className="ticket-verify-title">{isValid ? 'Valid Ticket' : result?.booking_status === 'CANCELLED' ? 'Ticket Cancelled' : 'Ticket Not Confirmed'}</h1>
        <p className="ticket-verify-ref">{result.booking_reference}</p>

        <div className="ticket-details" style={{ marginTop: '1.5rem' }}>
          <div className="ticket-row"><span className="ticket-row__label">Movie</span><span className="ticket-row__value">{result.movie_title}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Theatre</span><span className="ticket-row__value">{result.theatre_name}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Screen</span><span className="ticket-row__value">{result.screen_name}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Date</span><span className="ticket-row__value">{result.show_date}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Time</span><span className="ticket-row__value">{result.show_start_time} – {result.show_end_time}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Seats</span><span className="ticket-row__value">{result.seat_labels}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Booking status</span><span className="ticket-row__value">{result.booking_status}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Payment method</span><span className="ticket-row__value">{result.payment_method || '—'}</span></div>
          <div className="ticket-row"><span className="ticket-row__label">Payment status</span><span className="ticket-row__value">{result.payment_status}</span></div>
        </div>

        {result.payment_status !== 'CAPTURED' && result.payment_method === 'CASH' && (
          <div className="ticket-cash-notice" style={{ marginTop: '1.5rem' }}>
            ⚠️ Payment is pending. Customer must pay at the counter.
          </div>
        )}

        <Link className="button button--primary" to="/" style={{ marginTop: '2rem', display: 'inline-block' }}>Go to BookOurShow</Link>
      </div>
    </main>
  );
}
