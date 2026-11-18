import { useEffect, useRef, useState, useCallback } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { apiRequest } from '../lib/api';
import { useAuth } from '../context/AuthContext';

const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });

function TicketHeader() {
  return (
    <div className="ticket-header">
      <span className="ticket-brand">🎬 BookOurShow</span>
      <span className="ticket-label">MOVIE TICKET</span>
    </div>
  );
}

function TicketRow({ label, value }) {
  if (!value) return null;
  return (
    <div className="ticket-row">
      <span className="ticket-row__label">{label}</span>
      <span className="ticket-row__value">{value}</span>
    </div>
  );
}

function TicketBadge({ status }) {
  const isConfirmed = status === 'CONFIRMED';
  return (
    <span className={`ticket-badge ${isConfirmed ? 'ticket-badge--confirmed' : 'ticket-badge--pending'}`}>
      {isConfirmed ? '✓ CONFIRMED' : status}
    </span>
  );
}

export function TicketPage() {
  const { bookingId } = useParams();
  const { session } = useAuth();
  const navigate = useNavigate();
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);
  const printRef = useRef(null);

  const verifyUrl = ticket
    ? `${window.location.origin}/tickets/verify/${ticket.ticket_token}`
    : '';

  const load = useCallback(() => {
    if (!session?.access_token) return;
    setLoading(true);
    setError('');
    apiRequest(`/bookings/${bookingId}/ticket`, session.access_token)
      .then((data) => { setTicket(data); setLoading(false); })
      .catch((reason) => { setError(reason.message); setLoading(false); });
  }, [bookingId, session?.access_token]);

  useEffect(() => { load(); }, [load]);

  function handlePrint() {
    window.print();
  }

  async function cancelTicket() {
    if (!ticket || cancelling) return;
    if (!window.confirm('Cancel this ticket? It will no longer pass QR verification. Any counter refund must be handled by theatre staff.')) return;
    setCancelling(true);
    try {
      await apiRequest(`/bookings/${bookingId}/cancel`, session.access_token, { method: 'POST' });
      navigate(`/booking/${bookingId}`, { replace: true });
    } catch (reason) {
      setError(reason.message);
    } finally { setCancelling(false); }
  }

  if (loading) {
    return (
      <main className="page-container show-page" role="status">
        <p>Loading your ticket…</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page-container show-page">
        <div className="shows-error">
          <h1>Could not load ticket</h1>
          <p>{error}</p>
          <button className="button button--primary" onClick={load}>Retry</button>
          <Link className="button button--primary" to={`/booking/${bookingId}`}>Back to booking</Link>
        </div>
      </main>
    );
  }

  if (!ticket) return null;

  return (
    <main className="page-container show-page ticket-page">
      <div className="ticket-actions no-print">
        <button className="button button--quiet" type="button" onClick={() => navigate(`/booking/${bookingId}`)}>
          ← Back to booking
        </button>
        <button className="button button--primary" type="button" onClick={handlePrint}>
          🖨 Print / Save ticket
        </button>
        <Link className="button button--quiet" to="/profile">My bookings</Link>
        {ticket.status === 'CONFIRMED' && ticket.payment_method === 'CASH' && (
          <button className="button button--quiet" type="button" disabled={cancelling} onClick={cancelTicket}>
            {cancelling ? 'Cancelling…' : 'Cancel ticket'}
          </button>
        )}
      </div>

      <div className="ticket-card" ref={printRef}>
        <TicketHeader />

        {ticket.movie_poster_url && (
          <div className="ticket-poster-row">
            <img
              className="ticket-poster"
              src={ticket.movie_poster_url}
              alt={`${ticket.movie_title} poster`}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            <div className="ticket-movie-info">
              <h1 className="ticket-movie-title">{ticket.movie_title}</h1>
              {ticket.movie_duration_minutes != null && (
                <p className="ticket-meta">
                  {Math.floor(ticket.movie_duration_minutes / 60)}h {ticket.movie_duration_minutes % 60}m
                  {ticket.movie_certification ? ` · ${ticket.movie_certification}` : ''}
                </p>
              )}
            </div>
          </div>
        )}

        {!ticket.movie_poster_url && (
          <div className="ticket-movie-info ticket-movie-info--no-poster">
            <h1 className="ticket-movie-title">{ticket.movie_title}</h1>
            {ticket.movie_duration_minutes != null && (
              <p className="ticket-meta">
                {Math.floor(ticket.movie_duration_minutes / 60)}h {ticket.movie_duration_minutes % 60}m
                {ticket.movie_certification ? ` · ${ticket.movie_certification}` : ''}
              </p>
            )}
          </div>
        )}

        <div className="ticket-divider"><span>◈</span></div>

        <div className="ticket-details">
          <TicketRow label="Theatre" value={ticket.theatre_name} />
          <TicketRow label="Location" value={ticket.theatre_address} />
          <TicketRow label="Screen" value={ticket.screen_name} />
          <TicketRow label="Date" value={ticket.show_date} />
          <TicketRow label="Time" value={`${ticket.show_start_time} – ${ticket.show_end_time}`} />
        </div>

        <div className="ticket-divider"><span>◈</span></div>

        <div className="ticket-details">
          <TicketRow label="Booking reference" value={ticket.booking_reference} />
          <TicketRow label="Ticket token" value={ticket.ticket_token} />
          {ticket.customer_name && <TicketRow label="Name" value={ticket.customer_name} />}
          <TicketRow label="Seats" value={`${ticket.seat_labels} (${ticket.seat_count})`} />
          <TicketRow label="Total amount" value={money.format(Number(ticket.total_amount))} />
          <TicketRow label="Booked on" value={new Date(ticket.created_at).toLocaleString('en-IN')} />
        </div>

        <div className="ticket-divider"><span>◈</span></div>

        <div className="ticket-payment-row">
          <div>
            <div className="ticket-payment-method">
              {ticket.payment_method === 'CASH' ? '💵 CASH' : '💳 ' + ticket.payment_method}
            </div>
            <div className={`ticket-payment-status ${ticket.payment_method === 'CASH' ? 'ticket-payment-status--pending' : 'ticket-payment-status--paid'}`}>
              {ticket.payment_status}
            </div>
            <TicketBadge status={ticket.status} />
          </div>

          <div className="ticket-qr">
            <QRCodeSVG
              value={verifyUrl}
              size={128}
              level="M"
              includeMargin={true}
              bgColor="#ffffff"
              fgColor="#111827"
            />
            <p className="ticket-qr__hint">Scan to verify</p>
          </div>
        </div>

        {ticket.payment_method === 'CASH' && (
          <div className="ticket-cash-notice">
            ⚠️ Please pay at the theatre counter before the show.
          </div>
        )}

        <div className="ticket-footer">
          Issued by BookOurShow · This ticket is non-transferable
        </div>
      </div>
    </main>
  );
}
