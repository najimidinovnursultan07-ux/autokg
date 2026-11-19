import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { homeForRole } from '../../utils/roles.js'
import { LoadingState } from '../common/States.jsx'

export default function GuestRoute() {
  const { user, isAuthenticated, loading } = useAuth()
  if (loading) return <LoadingState label="Проверяем сессию…" />
  return isAuthenticated ? <Navigate to={homeForRole(user)} replace /> : <Outlet />
}
