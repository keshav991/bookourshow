import { useState } from 'react';
import { BrowserRouter, Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { Footer } from './components/Footer';
import { Navbar } from './components/Navbar';
import { SecondaryNavbar } from './components/SecondaryNavbar';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Home } from './pages/Home';
import { InfoPage } from './pages/InfoPage';
import { LoginPage } from './pages/LoginPage';
import { MovieDetails } from './pages/MovieDetails';
import { Movies } from './pages/Movies';
import { RegisterPage } from './pages/RegisterPage';
import { ProfilePage } from './pages/ProfilePage';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { MovieShowsPage } from './pages/MovieShowsPage';
import { ShowDetailsPage } from './pages/ShowDetailsPage';
import { BookingDetailsPage } from './pages/BookingDetailsPage';

function SiteLayout() {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <>
      <Navbar searchQuery={searchQuery} onSearchChange={setSearchQuery} />
      <SecondaryNavbar />
      <Outlet context={{ searchQuery, setSearchQuery }} />
      <Footer />
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
       <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<Home />} />
          <Route path="movies" element={<Movies />} />
          <Route path="movie/:id" element={<MovieDetails />} />
          <Route path="movie/:movieId/shows" element={<MovieShowsPage />} />
          <Route path="show/:showId" element={<ShowDetailsPage />} />
          <Route path="booking/:bookingId" element={<ProtectedRoute><BookingDetailsPage /></ProtectedRoute>} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="auth/callback" element={<AuthCallbackPage />} />
          <Route path="reset-password" element={<ResetPasswordPage />} />
          <Route path="profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="info/:topic" element={<InfoPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
       </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
