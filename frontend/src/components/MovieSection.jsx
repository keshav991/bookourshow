import { ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { MovieCard } from './MovieCard';

export function MovieSection({ title, movies, to, action = 'View all' }) {
  if (!movies.length) return null;

  return (
    <section className="movie-section">
      <div className="section-heading">
        <h2>{title}</h2>
        {to && <Link to={to}>{action}<ArrowRight size={16} /></Link>}
      </div>
      <div className="movie-grid">
        {movies.map((movie) => <MovieCard key={movie.id} movie={movie} />)}
      </div>
    </section>
  );
}
