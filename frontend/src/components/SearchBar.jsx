import { Search, X } from 'lucide-react';

export function SearchBar({ value, onChange }) {
  return (
    <label className="search-box">
      <Search size={18} aria-hidden="true" />
      <input
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Search for movies, events and more"
        aria-label="Search movies"
      />
      {value && (
        <button type="button" onClick={() => onChange('')} aria-label="Clear search">
          <X size={17} />
        </button>
      )}
    </label>
  );
}
