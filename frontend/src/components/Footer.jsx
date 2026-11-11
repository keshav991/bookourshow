import { Facebook, Instagram, Ticket, Youtube } from 'lucide-react';
import { Link } from 'react-router-dom';

const footerLinks = [
  ['About us', 'about'],
  ['Contact', 'contact'],
  ['Help & support', 'support'],
  ['Privacy policy', 'privacy'],
  ['Terms & conditions', 'terms'],
];

export function Footer() {
  return (
    <footer className="site-footer">
      <div className="page-container site-footer__top">
        <Link className="brand brand--footer" to="/">
          <span className="brand__mark"><Ticket size={21} /></span>
          <span>BookOur<span className="brand__accent">Show</span></span>
        </Link>
        <p>Your next great story starts here.</p>
        <div className="site-footer__social" aria-label="Social media">
          <span title="Social link coming soon"><Instagram size={18} /></span>
          <span title="Social link coming soon"><Facebook size={18} /></span>
          <span title="Social link coming soon"><Youtube size={19} /></span>
        </div>
      </div>
      <div className="page-container site-footer__bottom">
        <nav aria-label="Footer links">
          {footerLinks.map(([label, topic]) => <Link key={topic} to={`/info/${topic}`}>{label}</Link>)}
        </nav>
        <p>© 2026 BookOurShow. All rights reserved.</p>
      </div>
    </footer>
  );
}
