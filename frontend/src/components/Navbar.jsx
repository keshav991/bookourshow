import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Film, Menu, X } from 'lucide-react';
import { LocationSelector } from './LocationSelector';
import { SearchBar } from './SearchBar';
import { useAuth } from '../context/AuthContext';

export function Navbar({ searchQuery, onSearchChange }) {
  const [city, setCity] = useState('');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { user, profile, signOut } = useAuth();
  const navigate = useNavigate();

  async function handleSignOut() {
    await signOut();
    setMobileMenuOpen(false);
    navigate('/', { replace: true });
  }

  return (
    <header className="site-header">
      <div className="page-container site-header__main">
        <Link className="brand" to="/" aria-label="BookOurShow home">
          <span className="brand__mark"><Film size={21} /></span>
          <span>BookOur<span className="brand__accent">Show</span></span>
        </Link>

        <div className="site-header__search">
          <SearchBar value={searchQuery} onChange={onSearchChange} />
        </div>

        <div className="site-header__actions">
          <LocationSelector value={city} onChange={setCity} />
          {user ? <><Link className="signin-link" to="/profile">{profile?.full_name || 'My account'}</Link><button className="signin-link header-signout" type="button" onClick={handleSignOut}>Sign out</button></> : <><Link className="signin-link" to="/login">Sign in</Link><Link className="button button--primary header-register" to="/register">Register</Link></>}
        </div>

        <button
          className="mobile-menu-toggle"
          type="button"
          aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={mobileMenuOpen}
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          {mobileMenuOpen ? <X size={23} /> : <Menu size={23} />}
        </button>
      </div>
      <div className="page-container site-header__mobile-search">
        <SearchBar value={searchQuery} onChange={onSearchChange} />
      </div>
      {mobileMenuOpen && (
        <div className="mobile-menu">
          <LocationSelector value={city} onChange={setCity} />
          {user ? <><Link to="/profile" onClick={() => setMobileMenuOpen(false)}>My account</Link><button type="button" onClick={handleSignOut}>Sign out</button></> : <><Link to="/login" onClick={() => setMobileMenuOpen(false)}>Sign in</Link><Link to="/register" onClick={() => setMobileMenuOpen(false)}>Register</Link></>}
        </div>
      )}
    </header>
  );
}
