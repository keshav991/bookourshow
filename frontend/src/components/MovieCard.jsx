import { Link } from 'react-router-dom';
import { Star } from 'lucide-react';

const fallbackImage = '/images/poster-fallback.svg';

export function MovieCard({ movie, compact = false }) {
  return (
    <Link to={`/movie/${movie.id}`} className={`movie-card${compact ? ' movie-card--compact' : ''}`}>
      <div className="movie-card__poster-wrap">
        <img
          className="movie-card__poster"
          src={movie.poster || fallbackImage}
          alt={`${movie.title} poster`}
          loading="lazy"
          onError={(event) => {
            event.currentTarget.onerror = null;
            event.currentTarget.src = fallbackImage;
          }}
        />
        {movie.status === 'upcoming' && <span className="movie-card__badge">Coming soon</span>}
        {movie.status !== 'upcoming' && movie.rating && <span className="movie-card__rating"><Star size={14} fill="currentColor" /> {movie.rating}</span>}
      </div>
      <div className="movie-card__content">
        <h3>{movie.title}</h3>
        {movie.genres?.length ? <p>{movie.genres.slice(0, 2).join(' · ')}</p> : null}
        <span>{movie.status === 'upcoming' ? movie.releaseDate : (movie.language || []).join(', ')}</span>
        {movie.status === 'now-showing' && <span className="movie-card__action">Book tickets <span aria-hidden="true">→</span></span>}
      </div>
    </Link>
  );
}
