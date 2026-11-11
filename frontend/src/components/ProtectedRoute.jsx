import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function ProtectedRoute({ children }) {
  const { loading, user } = useAuth();
  const location = useLocation();
  if (loading) return <main className="page-loading" role="status">Checking your session…</main>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return children;
}
