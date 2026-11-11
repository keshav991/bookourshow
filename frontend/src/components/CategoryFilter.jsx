import { X } from 'lucide-react';

export function CategoryFilter({ categories, selected, onSelect }) {
  return (
    <div className="category-filter" id="categories">
      <div className="section-heading section-heading--small">
        <div>
          <h2>Browse by genre</h2>
          <p>Find a story for every mood.</p>
        </div>
        {selected !== 'All' && (
          <button className="clear-filter" type="button" onClick={() => onSelect('All')}>
            <X size={15} /> Clear filter
          </button>
        )}
      </div>
      <div className="category-list" role="group" aria-label="Filter movies by genre">
        {['All', ...categories].map((category) => (
          <button
            key={category}
            className={`category-chip${selected === category ? ' is-selected' : ''}`}
            type="button"
            aria-pressed={selected === category}
            onClick={() => onSelect(category)}
          >
            {category}
          </button>
        ))}
      </div>
    </div>
  );
}
