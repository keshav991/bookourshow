const poster = (path) => `https://image.tmdb.org/t/p/w500/${path}`;
const backdrop = (path) => `https://image.tmdb.org/t/p/w1280/${path}`;

// Static Phase 1 demo catalog. Replace these records with API data in a later phase.
export const movies = [
  {
    id: 'dune-part-two',
    title: 'Dune: Part Two',
    description: 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.',
    genres: ['Science Fiction', 'Adventure', 'Drama'],
    language: ['English', 'Hindi'],
    duration: '2h 46m',
    rating: '8.5',
    releaseDate: 'March 1, 2024',
    status: 'now-showing',
    cast: ['Timothée Chalamet', 'Zendaya', 'Rebecca Ferguson'],
    director: 'Denis Villeneuve',
    poster: poster('1pdfLvkbY9ohJlCjQH2CZjjYVvJ.jpg'),
    backdrop: backdrop('xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg'),
    featured: true,
  },
  {
    id: 'oppenheimer',
    title: 'Oppenheimer',
    description: 'The story of J. Robert Oppenheimer and the scientific team behind the first atomic bomb.',
    genres: ['Drama', 'History', 'Thriller'],
    language: ['English'],
    duration: '3h 0m',
    rating: '8.3',
    releaseDate: 'July 21, 2023',
    status: 'now-showing',
    cast: ['Cillian Murphy', 'Emily Blunt', 'Robert Downey Jr.'],
    director: 'Christopher Nolan',
    poster: poster('ptpr0kGAckfQkJeJIt8st5dglvd.jpg'),
    backdrop: backdrop('fm6KqXpk3M2HVveHwCrBSSBaO0V.jpg'),
    featured: true,
  },
  {
    id: 'spider-verse',
    title: 'Spider-Man: Across the Spider-Verse',
    description: 'Miles Morales travels across the multiverse and meets a team of Spider-People protecting its existence.',
    genres: ['Action', 'Adventure', 'Science Fiction'],
    language: ['English', 'Hindi'],
    duration: '2h 20m',
    rating: '8.7',
    releaseDate: 'June 2, 2023',
    status: 'now-showing',
    cast: ['Shameik Moore', 'Hailee Steinfeld', 'Brian Tyree Henry'],
    director: 'Joaquim Dos Santos, Kemp Powers, Justin K. Thompson',
    poster: poster('8Vt6mWEReuy4Of61Lnj5Xj704m8.jpg'),
    backdrop: backdrop('14QbnygCuTO0vl7CAFmPf1fgZfV.jpg'),
    featured: true,
  },
  {
    id: 'interstellar',
    title: 'Interstellar',
    description: 'A team of explorers travels beyond this galaxy to discover whether mankind has a future among the stars.',
    genres: ['Adventure', 'Drama', 'Science Fiction'],
    language: ['English', 'Hindi'],
    duration: '2h 49m',
    rating: '8.7',
    releaseDate: 'November 7, 2014',
    status: 'now-showing',
    cast: ['Matthew McConaughey', 'Anne Hathaway', 'Jessica Chastain'],
    director: 'Christopher Nolan',
    poster: poster('gEU2QniE6E77NI6lCU6MxlNBvIx.jpg'),
    backdrop: backdrop('xJHokMbljvjADYdit5fK5VQsXEG.jpg'),
  },
  {
    id: 'barbie',
    title: 'Barbie',
    description: 'Barbie and Ken leave their perfect world behind and discover the joys and challenges of life in the real world.',
    genres: ['Comedy', 'Adventure', 'Romance'],
    language: ['English', 'Hindi'],
    duration: '1h 54m',
    rating: '7.0',
    releaseDate: 'July 21, 2023',
    status: 'now-showing',
    cast: ['Margot Robbie', 'Ryan Gosling', 'America Ferrera'],
    director: 'Greta Gerwig',
    poster: poster('iuFNMS8U5cb6xfzi51Dbkovj7vM.jpg'),
    backdrop: backdrop('ctMserH8g2SeOAnCw5gFjdQF8mo.jpg'),
  },
  {
    id: 'the-batman',
    title: 'The Batman',
    description: 'Batman uncovers corruption in Gotham City while pursuing a serial killer known as the Riddler.',
    genres: ['Action', 'Crime', 'Drama'],
    language: ['English', 'Hindi'],
    duration: '2h 56m',
    rating: '7.8',
    releaseDate: 'March 4, 2022',
    status: 'now-showing',
    cast: ['Robert Pattinson', 'Zoë Kravitz', 'Paul Dano'],
    director: 'Matt Reeves',
    poster: poster('74xTEgt7R36Fpooo50r9T25onhq.jpg'),
    backdrop: backdrop('b0PlSFdDwbyK0cf5RxwDpaOJQvQ.jpg'),
  },
  {
    id: 'echoes-tomorrow',
    title: 'Echoes of Tomorrow',
    description: 'A radio astronomer receives a message from the future that could change the course of humanity.',
    genres: ['Science Fiction', 'Thriller', 'Drama'],
    language: ['English'],
    duration: '2h 8m',
    rating: 'Coming soon',
    releaseDate: 'December 2026',
    status: 'upcoming',
    cast: ['Ava Laurent', 'Daniel Cho', 'Mira Patel'],
    director: 'Nina Calder',
    poster: '/images/poster-fallback.svg',
    backdrop: '/images/poster-fallback.svg',
  },
  {
    id: 'last-summer-light',
    title: 'The Last Summer Light',
    description: 'Three friends return to their coastal hometown for one final summer before life takes them in new directions.',
    genres: ['Romance', 'Drama'],
    language: ['English', 'Hindi'],
    duration: '1h 52m',
    rating: 'Coming soon',
    releaseDate: 'January 2027',
    status: 'upcoming',
    cast: ['Leah Morgan', 'Arjun Rao', 'Theo Martin'],
    director: 'Sofia Bennett',
    poster: '/images/poster-fallback.svg',
    backdrop: '/images/poster-fallback.svg',
  },
];

export const movieCategories = [
  'Action', 'Comedy', 'Drama', 'Romance', 'Thriller', 'Horror', 'Science Fiction', 'Adventure',
];

export const findMovie = (id) => movies.find((movie) => movie.id === id);
export const findMovieByTitle = (title) => movies.find((movie) => movie.title.toLowerCase() === title?.toLowerCase());

export function searchMovies(query, category = 'All', status = 'all') {
  const normalizedQuery = query.trim().toLowerCase();

  return movies.filter((movie) => {
    const searchableText = [
      movie.title,
      movie.description,
      ...movie.genres,
      ...movie.language,
      ...movie.cast,
      movie.director,
    ].join(' ').toLowerCase();
    const matchesQuery = !normalizedQuery || searchableText.includes(normalizedQuery);
    const matchesCategory = category === 'All' || movie.genres.includes(category);
    const matchesStatus = status === 'all' || movie.status === status;
    return matchesQuery && matchesCategory && matchesStatus;
  });
}
