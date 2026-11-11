import { Link } from 'react-router-dom';

const sections = ['Movies', 'Stream', 'Events', 'Plays', 'Sports', 'Activities'];

export function SecondaryNavbar() {
  return (
    <nav className="secondary-nav" aria-label="Explore">
      <div className="page-container secondary-nav__inner">
        {sections.map((section) => section === 'Movies' ? (
          <Link key={section} to="/movies">{section}</Link>
        ) : (
          <Link
            key={section}
            to="/movies"
            state={{ notice: `${section} discovery is coming soon.` }}
            className="secondary-nav__soon"
          >
            {section}<span>Coming soon</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}
