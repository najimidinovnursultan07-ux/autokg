import { AlertTriangle, Building2, CarFront, CreditCard, LogOut, Plus, Settings } from 'lucide-react'
import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext.jsx'

// Кабинет автосалона (role=dealer)
const navigation = [
  { label: 'Объявления', to: '/dashboard', icon: CarFront, end: true },
  { label: 'Добавить авто', to: '/dashboard/cars/new', icon: Plus },
  { label: 'Профиль салона', to: '/dashboard/profile', icon: Building2 },
  { label: 'История платежей', to: '/dashboard/payments', icon: CreditCard },
  { label: 'Настройки аккаунта', to: '/dashboard/account', icon: Settings },
]

export default function AccountLayout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)

  const logout = async () => {
    setLoggingOut(true)
    await signOut()
    navigate('/', { replace: true })
  }

  return (
    <div className="container account-layout">
      <aside className="account-sidebar">
        <div className="account-identity">
          <span className="account-avatar"><Building2 size={22} /></span>
          <span className="account-identity-copy">
            <strong>{user?.dealer_name || 'Автосалон'}</strong>
            <span>{user?.email}</span>
          </span>
        </div>
        <nav className="account-navigation" aria-label="Кабинет автосалона">
          {navigation.map(({ label, to, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `account-nav-link ${isActive ? 'account-nav-link--active' : ''}`}
            >
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
          <button type="button" className="account-nav-link account-logout" onClick={logout} disabled={loggingOut}>
            <LogOut size={17} />
            <span>{loggingOut ? 'Выходим…' : 'Выйти'}</span>
          </button>
        </nav>
      </aside>
      <main className="account-main">
        {user?.dealer_is_active === false && (
          <div className="form-alert dealer-blocked-alert" role="alert">
            <AlertTriangle size={17} />
            <span>Ваш автосалон отключён администратором: объявления скрыты с сайта, редактирование недоступно.</span>
          </div>
        )}
        <Outlet />
      </main>
    </div>
  )
}
