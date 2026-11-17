import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { LoadingState } from '../common/States.jsx'

export default function AdminRoute() {
  const { user, isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingState label="Проверяем права администратора…" />
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (user?.role !== 'admin' || user?.is_staff !== true) {
    return <Navigate to="/dashboard" replace />
  }
  return <Outlet />
}
