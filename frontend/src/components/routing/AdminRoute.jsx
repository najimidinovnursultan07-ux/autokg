import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { LoadingState } from '../common/States.jsx'

export default function AdminRoute() {
  const { user, isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingState label="Проверяем права администратора…" />

  if (!isAuthenticated || user?.role !== 'admin' || user?.is_staff !== true) {
    return <Navigate to="/admin/login" replace state={{ from: location }} />
  }

  return <Outlet />
}
