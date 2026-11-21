import { AlertTriangle, Building2, CarFront, Gem, LogOut, Plus, Settings } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { getMySubscription } from '../../api/subscriptions.js'
import { useAuth } from '../../context/AuthContext.jsx'

// Кабинет автосалона (role=dealer)
const navigation = [
  { label: 'Объявления', to: '/dashboard', icon: CarFront, end: true },
  { label: 'Добавить авто', to: '/dashboard/cars/new', icon: Plus },
  { label: 'Профиль салона', to: '/dashboard/profile', icon: Building2 },
  { label: 'Мой тариф', to: '/dashboard/subscription', icon: Gem },
  { label: 'Настройки аккаунта', to: '/dashboard/account', icon: Settings },
]

export default function AccountLayout() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const { pathname } = useLocation()
  // undefined — ещё загружается, null — тарифа нет
  const [subscription, setSubscription] = useState(undefined)

  const reloadSubscription = useCallback(() => (
    getMySubscription()
      .then((data) => setSubscription(data.subscription))
      .catch(() => {})
  ), [])

  useEffect(() => { reloadSubscription() }, [reloadSubscription, pathname])

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
        {user?.dealer_is_active !== false && subscription === null && !pathname.startsWith('/dashboard/subscription') && (
          <div className="form-alert dealer-blocked-alert" role="alert">
            <AlertTriangle size={17} />
            <span>Тариф не активен: объявления скрыты с сайта. <Link to="/dashboard/subscription">Продлить тариф</Link></span>
          </div>
        )}
        {subscription && subscription.days_left <= 3 && !pathname.startsWith('/dashboard/subscription') && (
          <div className="form-alert form-alert--warning" role="status">
            <AlertTriangle size={17} />
            <span>
              {subscription.is_trial ? 'Пробный период' : `Тариф «${subscription.plan.name}»`} заканчивается через {subscription.days_left} дн.
              {' '}<Link to="/dashboard/subscription">Продлить</Link>
            </span>
          </div>
        )}
        <Outlet context={{ subscription, reloadSubscription }} />
      </main>
    </div>
  )
}
