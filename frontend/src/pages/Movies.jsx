import { useEffect, useState } from 'react';
import { useLocation, useOutletContext, useSearchParams } from 'react-router-dom';
import { Clapperboard } from 'lucide-react';
import { apiRequest } from '../lib/api';
import { filterMovies, toCatalogMovie } from '../data/movieCatalog';
import { MovieCard } from '../components/MovieCard';

export function Movies() {
  const { searchQuery = '', setSearchQuery } = useOutletContext() || {};
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryKey, setRetryKey] = useState(0);
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const status = searchParams.get('status') || 'all';
  const recommendedOnly = searchParams.get('recommended') === 'true';
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    apiRequest('/movies')
      .then((items) => { if (active) setMovies(items.map(toCatalogMovie)); })
      .catch((reason) => { if (active) setError(reason.message || 'Unable to fetch movies.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [retryKey]);
  const results = filterMovies(movies, searchQuery, status)
    .filter((movie) => !recommendedOnly || movie.status === 'now-showing');
  const title = status === 'upcoming'
    ? 'Coming soon'
    : status === 'now-showing'
      ? 'Now showing'
      : recommendedOnly
        ? 'Recommended movies'
        : 'Explore movies';

  return (
    <main className="page-container listing-page">
      <div className="listing-heading">
        <div>
          <span className="eyebrow eyebrow--red">Discover</span>
          <h1>{title}</h1>
        </div>
        <p>{loading ? 'Loading movies…' : `${results.length} ${results.length === 1 ? 'movie' : 'movies'}`}</p>
      </div>
      {location.state?.notice && <p className="feature-notice" role="status">{location.state.notice}</p>}
      {error ? <div className="shows-error" role="alert"><h2>Could not load movies</h2><p>{error}</p><button className="button button--primary" onClick={() => setRetryKey((key) => key + 1)}>Try again</button></div> : null}
      {!error && loading ? <p className="empty-state" role="status" aria-live="polite">Loading movies…</p> : null}
      {!error && !loading && results.length ? (
        <div className="movie-grid movie-grid--listing">
          {results.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
        </div>
      ) : null}
      {!error && !loading && results.length === 0 ? (
        <div className="empty-state" role="status">
          <Clapperboard size={30} />
          <h2>{movies.length ? 'No matching movies' : 'No movies available'}</h2>
          <p>{movies.length ? 'Try another search.' : 'There are no movies in the catalogue yet.'}</p>
          {searchQuery && <button className="button button--primary" type="button" onClick={() => setSearchQuery?.('')}>Clear search</button>}
        </div>
      ) : null}
    </main>
  );
}
