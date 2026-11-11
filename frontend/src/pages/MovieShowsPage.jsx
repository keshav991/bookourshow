import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, MapPin } from 'lucide-react';
import { apiRequest } from '../lib/api';

const dateLabel = (value, options) => new Intl.DateTimeFormat('en-IN', { ...options, timeZone: 'Asia/Kolkata' }).format(new Date(`${value}T00:00:00+05:30`));
const timeLabel = (value) => new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit', timeZone: 'Asia/Kolkata' }).format(new Date(value));

export function MovieShowsPage() {
  const { movieId } = useParams();
  const [movie, setMovie] = useState(null);
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [theatres, setTheatres] = useState([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [showsLoading, setShowsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showsError, setShowsError] = useState('');
  const [retryKey, setRetryKey] = useState(0);

  useEffect(() => {
    let active = true;
    setPageLoading(true); setError('');
    Promise.all([
      apiRequest(`/movies/${movieId}`),
      apiRequest(`/shows/movie/${movieId}/dates`),
    ]).then(([movieInfo, availableDates]) => {
      if (!active) return;
      setMovie(movieInfo);
      const values = availableDates.map((item) => item.date);
      setDates(values);
      setSelectedDate((current) => values.includes(current) ? current : (values[0] || ''));
    }).catch((reason) => { if (active) setError(reason.message); })
      .finally(() => { if (active) setPageLoading(false); });
    return () => { active = false; };
  }, [movieId, retryKey]);

  useEffect(() => {
    if (!selectedDate) { setTheatres([]); setShowsLoading(false); return undefined; }
    let active = true;
    setShowsLoading(true); setShowsError('');
    apiRequest(`/shows/movie/${movieId}?date=${encodeURIComponent(selectedDate)}`)
      .then((result) => { if (active) setTheatres(result.theatres || []); })
      .catch((reason) => { if (active) { setShowsError(reason.message); setTheatres([]); } })
      .finally(() => { if (active) setShowsLoading(false); });
    return () => { active = false; };
  }, [movieId, selectedDate, retryKey]);

  if (pageLoading) return <main className="page-container show-page"><ShowPageSkeleton /></main>;
  if (error) return <main className="page-container show-page"><div className="shows-error"><h1>Could not load showtimes</h1><p>{error}</p><button className="button button--primary" onClick={() => setRetryKey((key) => key + 1)}>Try again</button></div></main>;
  if (!movie) return null;

  return <main className="page-container show-page">
    <Link className="show-back" to={`/movie/${movie.id}`}><ArrowLeft size={16} /> Back to movie</Link>
    <section className="show-movie-summary">
      <img src={movie.poster_url || '/images/poster-fallback.svg'} alt={`${movie.title} poster`} onError={(event) => { event.currentTarget.onerror = null; event.currentTarget.src = '/images/poster-fallback.svg'; }} />
      <div><span className="eyebrow eyebrow--red">Choose a show</span><h1>{movie.title}</h1>
        <p>{movie.language || 'Language not specified'}{movie.duration_minutes != null ? ` · ${Math.floor(movie.duration_minutes / 60)}h ${movie.duration_minutes % 60}m` : ''}</p>
      </div>
    </section>

    {dates.length > 0 ? <section className="show-dates" aria-label="Available show dates">
      <h2>Select a date</h2>
      <div className="show-date-list">
        {dates.map((value) => <button type="button" key={value} className={`show-date${selectedDate === value ? ' is-selected' : ''}`} aria-pressed={selectedDate === value} onClick={() => setSelectedDate(value)}>
          <span>{dateLabel(value, { weekday: 'short' })}</span><strong>{dateLabel(value, { day: '2-digit' })}</strong><span>{dateLabel(value, { month: 'short' })}</span>
        </button>)}
      </div>
    </section> : <section className="shows-empty" role="status"><h2>No upcoming showtimes</h2><p>There are no future showtimes available for this movie. Please check back later.</p></section>}

    {showsError ? <div className="shows-error" role="alert"><p>{showsError}</p><button className="button button--primary" onClick={() => setRetryKey((key) => key + 1)}>Retry</button></div> : null}
    {showsLoading ? <TheatreSkeletons /> : null}
    {!showsLoading && !showsError && selectedDate && theatres.length === 0 ? <section className="shows-empty" role="status"><h2>No showtimes on this date</h2><p>Choose another date to see available showtimes.</p></section> : null}
    {!showsLoading && !showsError && theatres.map((theatre) => <TheatreCard key={theatre.id} theatre={theatre} movieId={movieId} selectedDate={selectedDate} />)}
  </main>;
}

function TheatreCard({ theatre, movieId, selectedDate }) {
  return <article className="theatre-card">
    <div className="theatre-card__info"><h2>{theatre.name}</h2><p><MapPin size={14} />{[theatre.address, theatre.city, theatre.state, theatre.pincode].filter(Boolean).join(', ')}</p></div>
    <div className="theatre-card__shows">{theatre.shows.map((show) => <Link className="showtime-link" key={show.id} to={`/show/${show.id}`} state={{ returnTo: `/movie/${movieId}/shows?date=${selectedDate}` }}>
      <strong>{timeLabel(show.start_time)}</strong><span>{show.format} · {show.language}</span><small>{show.screen.name}</small>
    </Link>)}</div>
  </article>;
}

function TheatreSkeletons() {
  return <div className="theatre-skeletons" aria-label="Loading theatres" aria-busy="true">{[1, 2].map((n) => <div className="theatre-skeleton" key={n}><span /><span /><div>{[1, 2, 3].map((item) => <i key={item} />)}</div></div>)}</div>;
}

function ShowPageSkeleton() {
  return <div className="show-page-skeleton" aria-label="Loading movie and show dates" aria-busy="true"><div className="skeleton-summary"><i /><div><b /><b /><b /></div></div><div className="skeleton-dates"><i /><i /><i /><i /></div><TheatreSkeletons /></div>;
}
