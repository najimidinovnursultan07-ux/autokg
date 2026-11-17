import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'
import { LoadingState } from '../common/States.jsx'

export default function GuestRoute() {
  const { isAuthenticated, loading } = useAuth()
  if (loading) return <LoadingState label="Проверяем сессию…" />
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Outlet />
}
