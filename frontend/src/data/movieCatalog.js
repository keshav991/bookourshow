export function toCatalogMovie(movie) {
  const duration = movie.duration_minutes == null
    ? ''
    : `${Math.floor(movie.duration_minutes / 60)}h ${movie.duration_minutes % 60}m`;

  return {
    id: String(movie.id),
    title: movie.title,
    description: movie.description || '',
    genres: [],
    language: movie.language ? [movie.language] : [],
    duration,
    rating: '',
    releaseDate: movie.release_date || 'Release date unavailable',
    status: movie.status?.toLowerCase().replaceAll('_', '-') || 'upcoming',
    cast: [],
    director: '',
    poster: movie.poster_url || '/images/poster-fallback.svg',
    backdrop: movie.backdrop_url || movie.poster_url || '/images/poster-fallback.svg',
  };
}

export function filterMovies(movies, query = '', status = 'all') {
  const normalizedQuery = query.trim().toLowerCase();
  return movies.filter((movie) => {
    const matchesQuery = !normalizedQuery || [movie.title, movie.description, ...movie.language]
      .join(' ').toLowerCase().includes(normalizedQuery);
    return matchesQuery && (status === 'all' || movie.status === status);
  });
}
