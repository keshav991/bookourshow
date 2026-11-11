import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Clock3, MapPin } from 'lucide-react';
import { apiRequest } from '../lib/api';
import { useAuth } from '../context/AuthContext';

const localTime = (value) => new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(value));
const localDate = (value) => new Intl.DateTimeFormat('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Asia/Kolkata' }).format(new Date(`${value}T00:00:00+05:30`));

export function ShowDetailsPage() {
  const { showId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { user, session } = useAuth();
  const [show, setShow] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryKey, setRetryKey] = useState(0);
  const [seatMap, setSeatMap] = useState(null);
  const [seatLoading, setSeatLoading] = useState(true);
  const [seatError, setSeatError] = useState('');
  const [seatRetryKey, setSeatRetryKey] = useState(0);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [bookingBusy, setBookingBusy] = useState(false);
  const [bookingError, setBookingError] = useState('');
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    apiRequest(`/shows/${showId}`).then((data) => { if (active) setShow(data); })
      .catch((reason) => { if (active) setError(reason.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [showId, retryKey]);

  useEffect(() => {
    let active = true;
    setSeatLoading(true); setSeatError('');
    apiRequest(`/shows/${showId}/seats`).then((data) => { if (active) setSeatMap(data); })
      .catch((reason) => { if (active) { setSeatError(reason.message); setSeatMap(null); } })
      .finally(() => { if (active) setSeatLoading(false); });
    return () => { active = false; };
  }, [showId, seatRetryKey]);

  const backTo = location.state?.returnTo || (show ? `/movie/${show.movie.id}/shows?date=${show.show_date}` : '/movies');
  if (loading) return <main className="page-container show-page"><ShowDetailSkeleton /></main>;
  if (error) return <main className="page-container show-page"><div className="shows-error"><h1>Could not load show details</h1><p>{error}</p><button className="button button--primary" onClick={() => setRetryKey((key) => key + 1)}>Try again</button></div></main>;
  if (!show) return null;
  return <main className="page-container show-page show-detail-page">
    <Link className="show-back" to={backTo}><ArrowLeft size={16} /> Back to showtimes</Link>
    <span className="eyebrow eyebrow--red">Show details</span><h1>{show.movie.title}</h1>
    <section className="show-detail-card">
      <div><span className="show-detail-label">Theatre</span><h2>{show.theatre.name}</h2><p className="show-location"><MapPin size={15} />{[show.theatre.address, show.theatre.city, show.theatre.state, show.theatre.pincode].filter(Boolean).join(', ')}</p></div>
      <div className="show-detail-grid">
        <div><span className="show-detail-label">Date</span><strong>{localDate(show.show_date)}</strong></div>
        <div><span className="show-detail-label">Time</span><strong><Clock3 size={15} /> {localTime(show.start_time)} – {localTime(show.end_time)}</strong></div>
        <div><span className="show-detail-label">Screen</span><strong>{show.screen.name}</strong></div>
        <div><span className="show-detail-label">Language and format</span><strong>{show.language} · {show.format}</strong></div>
        <div><span className="show-detail-label">Status</span><strong className="show-status">{show.status}</strong></div>
      </div>
    </section>
    <section className="show-seat-map" aria-labelledby="show-seat-map-title">
      <div className="show-seat-map__heading"><div><span className="show-detail-label">Screen layout</span><h2 id="show-seat-map-title">Available seats</h2></div>{seatMap ? <span>{seatMap.screen.name} · {seatMap.seats.length} seats</span> : null}</div>
      {seatLoading ? <p className="show-seat-map__message" role="status">Loading seats…</p> : null}
      {seatError ? <div className="show-seat-map__message" role="alert"><p>{seatError}</p><button className="button button--primary" onClick={() => setSeatRetryKey((key) => key + 1)}>Retry</button></div> : null}
      {!seatLoading && !seatError && seatMap?.seats.length ? <SeatMap seats={seatMap.seats} selectedSeats={selectedSeats} onToggle={toggleSeat} /> : null}
      {!seatLoading && !seatError && seatMap?.seats.length === 0 ? <p className="show-seat-map__message" role="status">No seat records are available for this show.</p> : null}
      {!seatLoading && !seatError && seatMap?.seats.length ? <BookingSummary seats={seatMap.seats} selectedSeats={selectedSeats} user={user} busy={bookingBusy} error={bookingError} onContinue={continueBooking} /> : null}
    </section>
  </main>;

  function toggleSeat(seat) {
    setSelectedSeats((selected) => selected.includes(seat.show_seat_id)
      ? selected.filter((id) => id !== seat.show_seat_id)
      : [...selected, seat.show_seat_id]);
  }

  async function continueBooking() {
    if (!user) { navigate('/login', { state: { from: location } }); return; }
    if (!selectedSeats.length || !session?.access_token) return;
    setBookingBusy(true); setBookingError('');
    let locked = false;
    try {
      await apiRequest(`/shows/${showId}/seats/lock`, session.access_token, {
        method: 'POST', body: JSON.stringify({ show_seat_ids: selectedSeats }),
      });
      locked = true;
      const booking = await apiRequest(`/bookings/shows/${showId}`, session.access_token, {
        method: 'POST', body: JSON.stringify({ show_seat_ids: selectedSeats, idempotency_key: crypto.randomUUID() }),
      });
      navigate(`/booking/${booking.id}`, { state: { booking } });
    } catch (reason) {
      if (locked) {
        try { await apiRequest(`/shows/${showId}/seats/release`, session.access_token, { method: 'POST', body: JSON.stringify({ show_seat_ids: selectedSeats }) }); }
        catch { /* The server-side lock expiry remains the fallback. */ }
      }
      setBookingError(reason.message);
      setSeatRetryKey((key) => key + 1);
    } finally { setBookingBusy(false); }
  }
}

function SeatMap({ seats, selectedSeats, onToggle }) {
  const rows = seats.reduce((groups, seat) => {
    groups[seat.row_label] ||= [];
    groups[seat.row_label].push(seat);
    return groups;
  }, {});
  const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

  return <>
    <div className="seat-map-screen" aria-hidden="true">SCREEN</div>
    <div className="seat-map-rows" aria-label="Seat layout">
      {Object.entries(rows).map(([rowLabel, rowSeats]) => <div className="seat-map-row" key={rowLabel}>
        <span className="seat-map-row__label">{rowLabel}</span>
        <div className="seat-map-row__seats">{rowSeats.map((seat) => {
          const selected = selectedSeats.includes(seat.show_seat_id);
          const status = selected ? 'selected' : seat.status.toLowerCase();
          const label = `${rowLabel}${seat.seat_number}, ${seat.seat_type}, ${seat.status.toLowerCase()}, ${money.format(Number(seat.price))}`;
          const canSelect = seat.status === 'AVAILABLE' || selected;
          return <button type="button" key={seat.show_seat_id} className={`seat-tile seat-tile--${status} seat-tile--${seat.seat_type.toLowerCase()}`} disabled={!canSelect} aria-pressed={selected} aria-label={label} title={label} onClick={() => onToggle(seat)}>
            <span>{seat.seat_number}</span><small>{money.format(Number(seat.price))}</small>
          </button>;
        })}</div>
        <span className="seat-map-row__label">{rowLabel}</span>
      </div>)}
    </div>
    <div className="seat-map-legend" aria-label="Seat status legend">
      <span><i className="seat-tile--available" />Available</span>
      <span><i className="seat-tile--selected" />Selected</span>
      <span><i className="seat-tile--locked" />Locked</span>
      <span><i className="seat-tile--booked" />Booked</span>
    </div>
    <div className="seat-category-legend" aria-label="Seat categories">
      {['REGULAR', 'PREMIUM', 'RECLINER'].map((type) => {
        const example = seats.find((seat) => seat.seat_type === type);
        return example ? <span key={type}><i className={`seat-tile--${type.toLowerCase()}`} />{type} · {money.format(Number(example.price))}</span> : null;
      })}
    </div>
  </>;
}

function BookingSummary({ seats, selectedSeats, user, busy, error, onContinue }) {
  const selected = seats.filter((seat) => selectedSeats.includes(seat.show_seat_id));
  const total = selected.reduce((sum, seat) => sum + Number(seat.price), 0);
  const money = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 });
  return <div className="booking-summary">
    <div><span className="show-detail-label">Selected seats</span><strong>{selected.length ? selected.map((seat) => `${seat.row_label}${seat.seat_number}`).join(', ') : 'Choose seats to continue'}</strong></div>
    <div><span className="show-detail-label">Ticket total</span><strong>{money.format(total)}</strong></div>
    {error ? <p role="alert" className="booking-summary__error">{error}</p> : null}
    <button type="button" className="button button--primary" disabled={busy || selected.length === 0} onClick={onContinue}>
      {busy ? 'Reserving seats…' : user ? 'Continue to booking' : 'Sign in to book'}
    </button>
    <small>Seat prices are supplied by the show and checked again when your booking is created.</small>
  </div>;
}

function ShowDetailSkeleton() { return <div className="show-detail-skeleton" aria-label="Loading show details" aria-busy="true"><i /><i /><div>{[1, 2, 3, 4].map((x) => <b key={x} />)}</div></div>; }
