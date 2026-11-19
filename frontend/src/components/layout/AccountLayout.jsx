import {
  CarFront,
  CreditCard,
  Eye,
  EyeOff,
  Heart,
  LayoutDashboard,
  LogOut,
  Settings,
  UserRound,
} from 'lucide-react'
import { useState } from 'react'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { resolveMediaUrl } from '../../api/client.js'
import { useAuth } from '../../context/AuthContext.jsx'

const navigation = [
  { id: 'overview', label: 'Обзор', to: '/dashboard', icon: LayoutDashboard },
  { id: 'profile', label: 'Мой профиль', to: '/profile', icon: UserRound },
  { id: 'all', label: 'Мои объявления', to: '/my-cars', icon: CarFront },
  { id: 'active', label: 'Активные', to: '/my-cars?status=published', icon: Eye },
  { id: 'inactive', label: 'Неактивные', to: '/my-cars?status=inactive', icon: EyeOff },
  { id: 'favorites', label: 'Избранное', to: '/favorites', icon: Heart },
  { id: 'payments', label: 'История платежей', to: '/payment-history', icon: CreditCard },
  { id: 'settings', label: 'Настройки аккаунта', to: '/account-settings', icon: Settings },
]

function isCurrentRoute(item, location) {
  if (item.id === 'all') {
    const status = new URLSearchParams(location.search).get('status')
    return location.pathname === item.to && !status
  }
  if (item.id === 'active' || item.id === 'inactive') {
    const status = new URLSearchParams(location.search).get('status')
    return location.pathname === '/my-cars'
      && status === (item.id === 'active' ? 'published' : 'inactive')
  }
  return location.pathname === item.to
}

export default function AccountLayout() {
  const { user, signOut } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const initials = `${user?.first_name?.[0] || ''}${user?.last_name?.[0] || ''}`.toUpperCase()
  const photo = user?.profile_photo ? resolveMediaUrl(user.profile_photo) : ''

  const logout = async () => {
    setLoggingOut(true)
    await signOut()
    navigate('/', { replace: true })
  }

  return (
    <div className="container account-layout">
      <aside className="account-sidebar">
        <div className="account-identity">
          <span className="account-avatar">
            {photo ? <img src={photo} alt="" /> : initials || <UserRound size={22} />}
          </span>
          <span className="account-identity-copy">
            <strong>{[user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'Пользователь AutoKG'}</strong>
            <span>{user?.email}</span>
          </span>
        </div>
        <nav className="account-navigation" aria-label="Разделы личного кабинета">
          {navigation.map(({ id, label, to, icon: Icon }) => (
            <Link
              className={`account-nav-link ${isCurrentRoute({ id, to }, location) ? 'account-nav-link--active' : ''}`}
              to={to}
              key={id}
            >
              <Icon size={17} />
              <span>{label}</span>
            </Link>
          ))}
          <button type="button" className="account-nav-link account-logout" onClick={logout} disabled={loggingOut}>
            <LogOut size={17} />
            <span>{loggingOut ? 'Выходим…' : 'Выйти из аккаунта'}</span>
          </button>
        </nav>
      </aside>
      <main className="account-main"><Outlet /></main>
    </div>
  )
}
