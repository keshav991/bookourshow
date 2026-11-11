import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarDays, Clock3, Play } from 'lucide-react';
import { apiRequest } from '../lib/api';

export function MovieDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [movie, setMovie] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    apiRequest(`/movies/${id}`)
      .then((result) => { if (active) setMovie(result); })
      .catch((reason) => { if (active) setError(reason.message || 'Unable to load this movie.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [id]);

  if (loading) return <main className="page-container not-found" role="status">Loading movie…</main>;
  if (error || !movie) return (
    <main className="page-container not-found">
      <h1>{error ? 'Could not load movie' : 'Movie not found'}</h1>
      <p>{error || 'This movie is not available in the catalogue.'}</p>
      <Link className="button button--primary" to="/movies">Browse movies</Link>
    </main>
  );

  const isUpcoming = movie.status?.toUpperCase() === 'UPCOMING';
  const duration = movie.duration_minutes == null ? 'Duration unavailable' : `${Math.floor(movie.duration_minutes / 60)}h ${movie.duration_minutes % 60}m`;
  const releaseDate = movie.release_date || 'Release date unavailable';
  const trailerSearch = `https://www.youtube.com/results?search_query=${encodeURIComponent(`${movie.title} official trailer`)}`;

  return (
    <main className="movie-details">
      <section className="movie-details__hero">
        <img src={movie.backdrop_url || movie.poster_url || '/images/poster-fallback.svg'} alt="" onError={(event) => { event.currentTarget.style.display = 'none'; }} />
        <div className="movie-details__shade" />
        <div className="page-container movie-details__hero-content">
          <Link to="/movies" className="back-link"><ArrowLeft size={17} /> All movies</Link>
          <div className="movie-details__main">
            <img className="movie-details__poster" src={movie.poster_url || '/images/poster-fallback.svg'} alt={`${movie.title} poster`} onError={(event) => { event.currentTarget.onerror = null; event.currentTarget.src = '/images/poster-fallback.svg'; }} />
            <div className="movie-details__summary">
              <span className={`status-label${isUpcoming ? ' status-label--upcoming' : ''}`}>{isUpcoming ? 'Coming soon' : 'Now showing'}</span>
              <h1>{movie.title}</h1>
              <div className="movie-details__facts">
                <span><Clock3 size={16} /> {duration}</span>
                <span><CalendarDays size={16} /> {releaseDate}</span>
                {movie.certification ? <span>{movie.certification}</span> : null}
              </div>
              <p className="movie-details__language">{movie.language}</p>
              <div className="movie-details__actions">
                {!isUpcoming && <button className="button button--primary" type="button" onClick={() => navigate(`/movie/${movie.id}/shows`)}>Book tickets</button>}
                <a className="button button--outline-light" href={trailerSearch} target="_blank" rel="noreferrer"><Play size={16} /> Watch trailer</a>
              </div>
            </div>
          </div>
        </div>
      </section>
      <section className="page-container movie-details__body">
        <div className="movie-details__about"><h2>About the movie</h2><p>{movie.description || 'No description is available.'}</p></div>
      </section>
    </main>
  );
}
