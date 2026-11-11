import { MapPin } from 'lucide-react';

const cities = ['Bengaluru', 'Chennai', 'Delhi NCR', 'Hyderabad', 'Kochi', 'Kolkata', 'Mumbai', 'Pune'];

export function LocationSelector({ value, onChange }) {
  return (
    <label className="location-picker">
      <MapPin size={17} aria-hidden="true" />
      <select aria-label="Choose your city" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Choose city</option>
        {cities.map((city) => <option key={city} value={city}>{city}</option>)}
      </select>
    </label>
  );
}
