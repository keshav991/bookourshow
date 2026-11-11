import { Film } from 'lucide-react';
import { Link } from 'react-router-dom';

export function AuthFrame({ eyebrow = 'Your next great night out', title, subtitle, children }) {
  return <main className="auth-page page-container">
    <section className="auth-card">
      <Link to="/" className="auth-brand" aria-label="BookOurShow home"><span className="brand__mark"><Film size={21} /></span><span>BookOur<span className="brand__accent">Show</span></span></Link>
      <span className="eyebrow eyebrow--red">{eyebrow}</span>
      <h1>{title}</h1>
      <p className="auth-subtitle">{subtitle}</p>
      {children}
    </section>
  </main>;
}

export function AuthMessage({ children, type = 'error' }) {
  return children ? <p className={`auth-message auth-message--${type}`} role={type === 'error' ? 'alert' : 'status'}>{children}</p> : null;
}
