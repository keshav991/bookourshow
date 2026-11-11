import { Link } from 'react-router-dom';
import { Film } from 'lucide-react';

export function LoginPlaceholder() {
  return (
    <main className="placeholder-page page-container">
      <span className="brand__mark"><Film size={22} /></span>
      <span className="eyebrow eyebrow--red">Coming in Phase 2</span>
      <h1>Sign in to BookOurShow</h1>
      <p>Account sign-in will be added in the next phase. You can explore the movie catalog now.</p>
      <div><Link className="button button--primary" to="/movies">Browse movies</Link><Link className="text-link" to="/register">Create account</Link></div>
    </main>
  );
}
