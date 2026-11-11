import { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { CalendarDays, Clapperboard, Flame } from 'lucide-react';
import { apiRequest } from '../lib/api';
import { filterMovies, toCatalogMovie } from '../data/movieCatalog';
import { HeroCarousel } from '../components/HeroCarousel';
import { MovieSection } from '../components/MovieSection';

export function Home() {
  const { searchQuery = '', setSearchQuery } = useOutletContext() || {};
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retryKey, setRetryKey] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true); setError('');
    apiRequest('/movies')
      .then((items) => { if (active) setMovies(items.map(toCatalogMovie)); })
      .catch((reason) => { if (active) setError(reason.message || 'Unable to fetch movies.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [retryKey]);
  const filteredMovies = filterMovies(movies, searchQuery);
  const featured = filteredMovies.slice(0, 5);
  const recommended = filteredMovies.slice(0, 3);
  const nowShowing = filteredMovies.filter((movie) => movie.status === 'now-showing');
  const upcoming = filteredMovies.filter((movie) => movie.status === 'upcoming');
  const hasFilter = Boolean(searchQuery.trim());

  return (
    <main>
      <HeroCarousel movies={featured} />
      <div className="page-container home-content">
        {error ? <div className="shows-error" role="alert"><h2>Could not load movies</h2><p>{error}</p><button className="button button--primary" onClick={() => setRetryKey((key) => key + 1)}>Try again</button></div> : null}
        {!error && loading ? <p className="empty-state" role="status" aria-live="polite">Loading movies…</p> : null}
        {!error && !loading && hasFilter && filteredMovies.length === 0 && (
          <div className="empty-state" role="status">
            <Clapperboard size={30} />
            <h2>No movies found</h2>
            <p>Try another title.</p>
            <button className="button button--primary" type="button" onClick={() => setSearchQuery?.('')}>Clear search</button>
          </div>
        )}
        {!error && !loading && searchQuery.trim() ? (
          <MovieSection title="Search results" movies={filteredMovies} />
        ) : !error && !loading ? (
          <>
            <MovieSection title="Recommended movies" movies={recommended} to="/movies?recommended=true" />
            <MovieSection title="Now showing" movies={nowShowing} to="/movies?status=now-showing" action="View all" />
            <MovieSection title="Coming soon" movies={upcoming} to="/movies?status=upcoming" action="View all" />
          </>
        ) : null}
        {!error && !loading && !hasFilter && (
          <div className="home-note"><CalendarDays size={18} /> Movies currently available in the catalogue</div>
        )}
      </div>
      <div className="home-callout">
        <div className="page-container home-callout__inner">
          <span><Flame size={20} /> A better night out starts here</span>
          <p>Explore the latest stories and find your next favorite film.</p>
        </div>
      </div>
    </main>
  );
}
