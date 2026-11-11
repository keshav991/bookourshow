import { Link } from 'react-router-dom';
import { Film } from 'lucide-react';

export function RegisterPlaceholder() {
  return (
    <main className="placeholder-page page-container">
      <span className="brand__mark"><Film size={22} /></span>
      <span className="eyebrow eyebrow--red">Coming in Phase 2</span>
      <h1>Create your account</h1>
      <p>Registration will be added in the next phase. For now, discover films and save a movie details page for later.</p>
      <div><Link className="button button--primary" to="/movies">Explore movies</Link><Link className="text-link" to="/login">Back to sign in</Link></div>
    </main>
  );
}
