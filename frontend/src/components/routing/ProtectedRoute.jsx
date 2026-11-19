import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { homeForRole } from '../../utils/roles.js'
import { LoadingState } from '../common/States.jsx'

/**
 * Защита маршрутов по роли (это только UX — права всё равно проверяет бэкенд).
 * roles: ['admin'] | ['dealer'] | undefined (любой авторизованный).
 */
export default function ProtectedRoute({ roles }) {
  const { user, isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingState label="Проверяем доступ…" />
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  if (roles) {
    const isAdmin = user?.role === 'admin' && user?.is_staff === true
    const allowed = roles.some((role) => (role === 'admin' ? isAdmin : user?.role === role))
    if (!allowed) return <Navigate to={homeForRole(user)} replace />
  }
  return <Outlet />
}
