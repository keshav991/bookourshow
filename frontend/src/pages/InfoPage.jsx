import { Link, useParams } from 'react-router-dom';

const pageContent = {
  about: ['About BookOurShow', 'A movie discovery experience built to help you find your next great story.'],
  contact: ['Contact', 'Contact details will be published here when the service launches.'],
  support: ['Help & support', 'Support resources will be available here when bookings launch.'],
  privacy: ['Privacy policy', 'The privacy policy will be published before account features launch.'],
  terms: ['Terms & conditions', 'Terms will be published before ticket booking becomes available.'],
};

export function InfoPage() {
  const { topic } = useParams();
  const [title, description] = pageContent[topic] || ['Information', 'This page is not available.'];
  return (
    <main className="page-container info-page">
      <span className="eyebrow eyebrow--red">BookOurShow</span>
      <h1>{title}</h1>
      <p>{description}</p>
      <Link className="text-link" to="/">Return to movies</Link>
    </main>
  );
}
