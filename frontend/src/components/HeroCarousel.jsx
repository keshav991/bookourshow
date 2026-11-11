import { useState } from 'react';
import { ArrowLeft, ArrowRight, Play, Star } from 'lucide-react';
import { Link } from 'react-router-dom';

export function HeroCarousel({ movies }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const movie = movies[activeIndex];

  if (!movie) return null;

  const move = (direction) => {
    setActiveIndex((current) => (current + direction + movies.length) % movies.length);
  };
  const trailerSearch = `https://www.youtube.com/results?search_query=${encodeURIComponent(`${movie.title} official trailer`)}`;

  return (
    <section className="hero-carousel" aria-label="Featured movies">
      <img
        key={movie.id}
        className="hero-carousel__image"
        src={movie.backdrop || movie.poster}
        alt=""
        onError={(event) => { event.currentTarget.style.display = 'none'; }}
      />
      <div className="hero-carousel__shade" />
      <div className="hero-carousel__content page-container">
        <span className="eyebrow">Featured film</span>
        <h1>{movie.title}</h1>
        <div className="hero-carousel__meta">
          {movie.rating ? <span><Star size={15} fill="currentColor" /> {movie.rating}</span> : null}
          {movie.genres?.length ? <span>{movie.genres.slice(0, 3).join(' · ')}</span> : null}
          <span>{(movie.language || []).join(', ')}</span>
        </div>
        <p>{movie.description}</p>
        <div className="hero-carousel__actions">
          <a className="button button--light" href={trailerSearch} target="_blank" rel="noreferrer">
            <Play size={16} fill="currentColor" /> Watch trailer
          </a>
          <Link className="button button--outline-light" to={`/movie/${movie.id}`}>Explore movie</Link>
        </div>
      </div>
      <div className="hero-carousel__controls">
        <button type="button" aria-label="Previous featured movie" onClick={() => move(-1)}><ArrowLeft size={19} /></button>
        <div className="hero-carousel__dots" aria-label={`Slide ${activeIndex + 1} of ${movies.length}`}>
          {movies.map((item, index) => (
            <button
              key={item.id}
              type="button"
              aria-label={`Show ${item.title}`}
              aria-current={index === activeIndex ? 'true' : undefined}
              className={index === activeIndex ? 'is-active' : ''}
              onClick={() => setActiveIndex(index)}
            />
          ))}
        </div>
        <button type="button" aria-label="Next featured movie" onClick={() => move(1)}><ArrowRight size={19} /></button>
      </div>
    </section>
  );
}
